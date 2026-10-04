"""Hierarchical grader (ADR-0009): deterministic → rubric checks → local LLM → hosted.

Every attempt produces: an assessment_attempt row, `attempted` + `graded` events, one
competency_evidence row (via the kernel, which emits `evidenced`), a competency refresh, and an
FSRS review of the item (via the kernel, which emits `reviewed`). Feedback is literal and specific.
"""

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.answer_recovery import AnswerRecovery
from app.core.errors import AppError
from app.db import assessment_executions, workspace_requests
from app.db.events import EventWriter, Verb
from app.db.models import (
    Assessment,
    AssessmentAttempt,
    MemoryState,
    Session,
    SkillNode,
    WorkspaceRequest,
)
from app.kernel import competency, memory
from app.kernel import session as ksession
from app.models_ai.gateway import GatewayError, ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.models_ai.routing import NoModelReady
from app.orchestrator import assessment_content, prompts
from app.orchestrator.assessment_answers import feedback_snapshot, save_feedback
from app.orchestrator.assessment_execution import AssessmentExecution
from app.orchestrator.context import escape_data, learner_answer_block
from app.schemas.common import ActivityType, Domain, ObjectType
from app.schemas.grading import (
    AssessmentView,
    AttemptRequest,
    AttemptResult,
    CriterionResult,
    GradeResult,
)

DIMENSION_FOR_KIND = {
    "mcq": "recall",
    "cloze": "recall",
    "explain_back": "explanation",
    "transfer": "transfer",
    "challenge_planted_error": "application",
    "challenge_steelman": "transfer",
    "challenge_teach_back": "explanation",
    "challenge_calibration": "recall",
    "code": "application",
}
KIND_ORDER = ["mcq", "cloze", "explain_back"]
LLM_ESCALATE_BELOW = 0.6


def view(a: Assessment) -> AssessmentView:
    item = a.item_json
    if a.kind == "mcq":
        return AssessmentView(
            id=a.id,
            skill_id=a.skill_id,
            kind=a.kind,
            question=item["question"],
            options=item["options"],
        )
    if a.kind == "cloze":
        return AssessmentView(id=a.id, skill_id=a.skill_id, kind=a.kind, question=item["text"])
    if a.kind == "code":  # as a review card the exercise asks its check question (P8)
        return AssessmentView(
            id=a.id,
            skill_id=a.skill_id,
            kind=a.kind,
            question=str(item.get("check_question") or item.get("prompt") or ""),
            criteria=list(item.get("success_criteria") or []),
        )
    return AssessmentView(
        id=a.id,
        skill_id=a.skill_id,
        kind=a.kind,
        question=item["prompt"],
        criteria=list(item.get("criteria", [])) if a.kind.startswith("challenge_") else None,
    )


async def versioned_view(db: AsyncSession, a: Assessment) -> AssessmentView:
    content = await assessment_content.snapshot(db, a.id)
    result = view(assessment_content.assessment(content))
    return result.model_copy(update={"content_version": assessment_content.token(content)})


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_√() ]+", " ", s.lower())).strip()


def grade_mcq(item: dict[str, Any], answer: str) -> tuple[GradeResult, bool]:
    options: list[str] = item["options"]
    correct_idx = int(item["answer"])
    chosen: int | None = None
    a = answer.strip()
    if a.isdigit() and int(a) < len(options):
        chosen = int(a)
    else:
        for i, opt in enumerate(options):
            if _norm(opt) == _norm(a):
                chosen = i
    passed = chosen == correct_idx
    chosen_text = options[chosen] if chosen is not None else f"an unrecognised answer ({a[:40]})"
    expl = item.get("explanation", "")
    if passed:
        feedback = f"Correct: {options[correct_idx]}. {expl}".strip()
        next_step = "Next: explain in one sentence why the other options are wrong."
    else:
        feedback = f"Not correct. You chose {chosen_text}. The correct option is {options[correct_idx]}. {expl}".strip()
        next_step = (
            f"Next: without looking, say in one sentence why '{options[correct_idx]}' is right, "
            "then retry a similar item."
        )
    return (
        GradeResult(
            criterion_results=[
                CriterionResult(
                    criterion="selects the correct option", passed=passed, evidence=chosen_text
                )
            ],
            confidence=1.0,
            feedback=feedback,
            next_step=next_step,
        ),
        passed,
    )


def grade_cloze(item: dict[str, Any], answer: str) -> tuple[GradeResult, bool]:
    accepted = [_norm(x) for x in item["answers"]]
    a = _norm(answer)
    passed = bool(a) and any(
        a == acc or re.search(rf"(?<![a-z0-9]){re.escape(acc)}(?![a-z0-9])", a) for acc in accepted
    )
    if passed:
        feedback = f"Correct: '{item['answers'][0]}' fits the blank."
        next_step = "Next: say the whole sentence aloud from memory."
    else:
        feedback = (
            f"Not correct. You wrote '{answer.strip()[:60]}'. Expected: '{item['answers'][0]}'."
        )
        next_step = (
            f"Next: from memory, use '{item['answers'][0]}' in a sentence of your own, then retry."
        )
    return (
        GradeResult(
            criterion_results=[
                CriterionResult(
                    criterion="fills the blank with an accepted term",
                    passed=passed,
                    evidence=answer.strip()[:80],
                )
            ],
            confidence=1.0,
            feedback=feedback,
            next_step=next_step,
        ),
        passed,
    )


def rubric_checks(criteria: list[dict[str, Any]], answer: str) -> GradeResult:
    """Level 2: routing diagnostics, not semantic evidence except for explicit abstention."""
    low = answer.lower()
    results = []
    for c in criteria:
        kws = [k.lower() for k in c.get("keywords", [])]
        hits = [k for k in kws if k in low]
        results.append(
            CriterionResult(
                criterion=c["criterion"], passed=bool(hits), evidence=", ".join(hits) or "absent"
            )
        )
    # Lexical overlap cannot distinguish a causal explanation from a keyword list,
    # negation or a correct paraphrase. Only an explicit abstention is conclusive.
    abstained = answer.strip().casefold().rstrip(".!?") in {
        "",
        "no idea",
        "i don't know",
        "i do not know",
    }
    if abstained:
        for row in results:
            row.passed = False
            row.evidence = "No explanation submitted."
    return GradeResult(
        criterion_results=results,
        confidence=0.8 if abstained and results else 0.0,
        feedback=(
            "No explanation submitted."
            if abstained
            else "Keyword overlap alone cannot verify this explanation."
        ),
        next_step=(
            "Next: ask for one hint, then try a sentence in your own words."
            if abstained
            else "Next: check the explanation against each rubric criterion."
        ),
    )


class Grader:
    def __init__(
        self,
        db: AsyncSession,
        gateway: ModelGateway,
        recovery: AnswerRecovery | None = None,
        *,
        request_claim_id: str | None = None,
        execution: AssessmentExecution | None = None,
    ) -> None:
        self.db = db
        self.gateway = gateway
        self.recovery = recovery
        self.request_claim_id = request_claim_id
        self.execution = execution or AssessmentExecution()

    async def next_item(self, learner_id: str, skill_id: str) -> Assessment | None:
        """Rotate kinds (mcq → cloze → explain_back); prefer items never attempted, then the oldest attempt."""
        items = list(
            (
                await self.db.execute(
                    select(Assessment).where(
                        Assessment.skill_id == skill_id, Assessment.kind != "code"
                    )
                )
            ).scalars()
        )
        if not items:
            return None
        attempts = list(
            (
                await self.db.execute(
                    select(AssessmentAttempt).where(
                        AssessmentAttempt.learner_id == learner_id,
                        AssessmentAttempt.assessment_id.in_([i.id for i in items]),
                    )
                )
            ).scalars()
        )
        last_ts: dict[str, str] = {}
        for at in attempts:
            last_ts[at.assessment_id] = max(last_ts.get(at.assessment_id, ""), at.ts)
        items.sort(
            key=lambda i: (
                last_ts.get(i.id, ""),
                KIND_ORDER.index(i.kind) if i.kind in KIND_ORDER else 9,
            )
        )
        return items[0]

    async def _llm_grade(
        self,
        task: TaskClass,
        rubric: list[dict[str, Any]],
        prompt: str,
        answer: str,
        *,
        learner_id: str,
        session_id: str,
        reference: str | None = None,
    ) -> tuple[GradeResult, str] | None:
        criteria = [c["criterion"] for c in rubric]
        user = "\n\n".join(
            [
                prompts.grader_task("explain_back").strip(),
                "## Question\n" + escape_data(prompt),
                *(
                    ["## Reference answer (hidden from the learner)\n" + escape_data(reference)]
                    if reference
                    else []
                ),
                "## Rubric criteria\n" + "\n".join(f"- {c}" for c in criteria),
                "## Learner answer\n" + learner_answer_block(answer),
                "Return criterion_results in the same order as the rubric.",
            ]
        )
        messages = [
            Message(role="system", content=prompts.base_policy()),
            Message(role="user", content=user),
        ]
        try:
            # Entering the gateway can have external effects even if it raises.
            if self.request_claim_id is not None and not self.execution.gateway_entered:
                await assessment_executions.mark_inference_started(
                    self.db, learner_id, self.request_claim_id
                )
            self.execution.gateway_entered = True
            out = await self.gateway.complete(
                task,
                messages,
                response_model=GradeResult,
                learner_id=learner_id,
                session_id=session_id,
                metadata={"prompt_version": prompts.GRADER_VERSION},
                max_tokens=600,
            )
        except (GatewayError, NoModelReady):
            return None
        result = out.result.parsed
        if (
            not isinstance(result, GradeResult)
            or not criteria
            or len(result.criterion_results) != len(criteria)
            or any(not c.evidence.strip() for c in result.criterion_results)
        ):
            return None
        # Match identities rather than relabeling positional evidence: duplicate or
        # unknown rows must not silently stand in for an unassessed criterion.
        names = [name.strip().casefold() for name in criteria]
        returned = {c.criterion.strip().casefold(): c for c in result.criterion_results}
        if len(set(names)) != len(names) or set(returned) != set(names):
            return None
        result.criterion_results = [returned[name] for name in names]
        for row, name in zip(result.criterion_results, criteria, strict=True):
            row.criterion = name
        level = "hosted" if out.hosted else "local"
        return result, level

    async def grade(self, req: AttemptRequest, *, now: datetime | None = None) -> AttemptResult:
        db = self.db
        now = now or datetime.now(UTC)
        session: Session = await ksession.get(db, req.session_id)
        learner_id = session.learner_id
        a = await db.get(Assessment, req.assessment_id)
        if a is None:
            raise KeyError("assessment not found")
        content = await assessment_content.snapshot(db, a.id)
        if req.content_version is not None:
            if assessment_content.token(content) != req.content_version:
                raise AppError(
                    "assessment_content_changed_during_grading",
                    "Content changed after submission. No learning evidence was saved; "
                    "check the saved result before retrying.",
                    409,
                )
        a = assessment_content.assessment(content)
        question_snapshot = view(a).model_dump()
        question_snapshot["content_version"] = assessment_content.token(content)
        # Close all reads before inference; gateway accounting owns its short transactions.
        await db.commit()
        if self.request_claim_id is not None:
            await assessment_executions.prepare(
                db,
                learner_id,
                self.request_claim_id,
                request_json=req.model_dump(mode="json"),
                content_fingerprint=assessment_content.recovery_fingerprint(content),
            )
        item = a.item_json
        correct: bool | None
        rubric_version = None
        if a.kind == "mcq":
            result, correct = grade_mcq(item, req.answer)
            level = "deterministic"
        elif a.kind == "code":
            # P8: check results computed in the learner's browser sandbox (never on this host)
            from app.kernel import exercises

            result, correct = exercises.grade_code(item, req.answer)
            level = "deterministic"
        elif a.kind == "cloze":
            result, correct = grade_cloze(item, req.answer)
            level = "deterministic"
        else:
            criteria: list[dict[str, Any]] = content["criteria_json"] or []
            rubric_version = content["version"]
            result = rubric_checks(criteria, req.answer)
            level = "rubric"
            is_challenge = a.kind.startswith("challenge_")
            reference = str(item.get("hidden_key")) if is_challenge else None
            if a.kind == "explain_back" and item.get("expected_answer"):
                reference = str(item["expected_answer"])[:1200]
                if item.get("evidence_quote"):
                    reference += "\nSource excerpt: " + str(item["evidence_quote"])[:300]
            if is_challenge:
                result.confidence = 0.0  # challenges are always LLM-graded against the hidden key
            if result.confidence < LLM_ESCALATE_BELOW:
                llm = await self._llm_grade(
                    TaskClass.GRADE_SIMPLE,
                    criteria,
                    item["prompt"],
                    req.answer,
                    learner_id=learner_id,
                    session_id=session.id,
                    reference=reference,
                )
                if llm is not None:
                    result, level = llm
                if result.confidence < LLM_ESCALATE_BELOW and level != "hosted":
                    hosted = await self._llm_grade(
                        TaskClass.GRADE_RUBRIC,
                        criteria,
                        item["prompt"],
                        req.answer,
                        learner_id=learner_id,
                        session_id=session.id,
                        reference=reference,
                    )
                    if hosted is not None:
                        result, level = hosted
                if result.confidence < LLM_ESCALATE_BELOW:
                    raise AppError(
                        "grading_unavailable",
                        "The explanation could not be graded reliably. Your mastery and review "
                        "schedule have not changed. Try again, or check Models › Routing.",
                        503,
                    )
            correct = None if 0.0 < result.score < 1.0 else result.score == 1.0

        if self.request_claim_id is not None:
            # A failed acknowledgement may still mean the grade was persisted.
            # Never release this claim and accidentally grade the answer again.
            self.execution.result_persistence_started = True
            await assessment_executions.save_grade(
                db,
                learner_id,
                self.request_claim_id,
                grade_json={
                    "version": 1,
                    "graded_at": now.isoformat(),
                    "result": result.model_dump(mode="json"),
                    "correct": correct,
                    "level": level,
                    "rubric_version": rubric_version,
                },
            )
        return await self.apply_result(
            req,
            content,
            result,
            correct=correct,
            level=level,
            rubric_version=rubric_version,
            now=now,
        )

    async def apply_result(
        self,
        req: AttemptRequest,
        content: dict[str, Any],
        result: GradeResult,
        *,
        correct: bool | None,
        level: str,
        rubric_version: int | None,
        now: datetime | None = None,
    ) -> AttemptResult:
        try:
            return await self._apply_result(
                req,
                content,
                result,
                correct=correct,
                level=level,
                rubric_version=rubric_version,
                now=now,
            )
        except BaseException:
            await self.db.rollback()
            raise

    async def _apply_result(
        self,
        req: AttemptRequest,
        content: dict[str, Any],
        result: GradeResult,
        *,
        correct: bool | None,
        level: str,
        rubric_version: int | None,
        now: datetime | None = None,
    ) -> AttemptResult:
        """Apply an already validated grade without entering the model gateway.

        Recovery callers must own the exact claim write lock and verify its
        stable content fingerprint before calling. No transaction ends here
        until the complete learning/outcome write set commits.
        """
        db = self.db
        now = now or datetime.now(UTC)
        if self.request_claim_id is not None:
            # Serialize initial application and explicit recovery; both can race
            # after the grade has been staged but before evidence is committed.
            await db.commit()
            await db.execute(
                update(WorkspaceRequest)
                .where(
                    WorkspaceRequest.id == self.request_claim_id,
                )
                .values(fingerprint=WorkspaceRequest.fingerprint)
            )
            claim = await db.get(WorkspaceRequest, self.request_claim_id, populate_existing=True)
            if claim is None or claim.session_id != req.session_id:
                raise AppError("request_unavailable", "The saved request is unavailable.", 410)
            if claim.response_json is not None:
                from app.orchestrator.assessment_requests import recovered_result

                saved = dict(claim.response_json)
                await db.commit()
                return await recovered_result(db, claim.learner_id, saved, self.recovery)
            staged = await assessment_executions.get_owned(db, claim.learner_id, claim.id)
            if staged is None or staged.phase != "grade_ready":
                raise AppError("request_unresolved", "No saved grade is available.", 409)
            if staged.content_fingerprint != assessment_content.recovery_fingerprint(content):
                raise AppError(
                    "assessment_content_changed",
                    "The saved grade no longer matches this question.",
                    409,
                )
        session = await ksession.get(db, req.session_id)
        learner_id = session.learner_id
        a = assessment_content.assessment(content)
        item = a.item_json
        question_snapshot = view(a).model_dump()
        question_snapshot["content_version"] = assessment_content.token(content)
        listening_meta = item.get("listening") if isinstance(item.get("listening"), dict) else None
        # one label everywhere: the attempt row, the graded event and the result say where the
        # verdict came from (a code exercise is checked in the learner's browser sandbox)
        route_label = "deterministic:client-pyodide" if a.kind == "code" else level
        if listening_meta is not None and listening_meta.get("validated") is False:
            # a model-proposed question nobody has checked: evidence at half weight, never Easy
            result.confidence = min(result.confidence, 0.5)
        score = result.score
        attempt = AssessmentAttempt(
            learner_id=learner_id,
            assessment_id=a.id,
            session_id=session.id,
            answer=req.answer,
            confidence_pre=req.confidence_pre,
            llm_result_json=result.model_dump() if level in ("local", "hosted") else None,
            deterministic_result_json=result.model_dump()
            if level in ("deterministic", "rubric")
            else None,
            grader_route=route_label,
            correct=correct,
            latency_ms=req.latency_ms,
            hint_count=req.hint_count,
        )
        # Model/gateway accounting has finished before the first learning write. This
        # short transaction owns attempt, events, evidence, FSRS, checkpoint and mastery.
        try:
            await assessment_content.guard_write(db, a.id, content)
            db.add(attempt)
            await db.flush()

            node = await db.get(SkillNode, a.skill_id)
            domain = (
                Domain(node.domain)
                if node is not None and node.domain in {d.value for d in Domain}
                else Domain.AI_ML
            )
            events = EventWriter(
                db, ksession.event_context(session, domain=domain, activity=ActivityType.RETRIEVAL)
            )
            await events.emit(
                Verb.ATTEMPTED,
                ObjectType.ITEM,
                a.id,
                result={
                    "correct": correct,
                    "confidence_pre": req.confidence_pre,
                    "latency_ms": req.latency_ms,
                    "hint_count": req.hint_count,
                    "answer_len": len(req.answer),
                },
                context={"item_type": a.kind, "node_id": a.skill_id},
                commit=False,
            )
            await events.emit(
                Verb.GRADED,
                ObjectType.ITEM,
                a.id,
                result={
                    "criterion_results": [
                        {"criterion": c.criterion, "passed": c.passed}
                        for c in result.criterion_results
                    ],
                    "score": score,
                    "misconception": result.misconception,
                    "confidence": result.confidence,
                    "feedback_len": len(result.feedback),
                },
                context={
                    "grader_level": route_label,
                    "prompt_version": prompts.GRADER_VERSION
                    if level in ("local", "hosted")
                    else None,
                    "rubric_version": rubric_version,
                },
                commit=False,
            )
            dimension = DIMENSION_FOR_KIND.get(a.kind, "recall")
            await competency.record_evidence(
                db,
                learner_id,
                a.skill_id,
                dimension,
                score,
                grader_level=level,
                confidence=result.confidence,
                attempt_id=attempt.id,
                events=events,
                commit=False,
            )
            review_item, _ = await memory.ensure_item(
                db,
                learner_id,
                a.skill_id,
                a.kind,
                {"ref": a.id, "assessment_id": a.id},
                now=now,
                commit=False,
            )
            rating = memory.rating_from_score(score, hint_count=req.hint_count)
            if (
                level == "rubric"
                or (listening_meta is not None and listening_meta.get("validated") is False)
                or (a.kind == "code" and result.confidence < 1.0)
            ):  # keyword overlap / unchecked item / code after the solution: never the longest interval
                rating = min(rating, memory.Rating.Good)
            await memory.review(
                db,
                learner_id,
                review_item.id,
                int(rating),
                now=now,
                latency_ms=req.latency_ms,
                events=events,
                commit=False,
            )
            if a.kind.startswith("challenge_") or a.kind == "code":
                # every challenge / code exercise ends with a delayed item (ADR-0003): ≥ +2 days
                from datetime import timedelta

                ms_row = (
                    await db.execute(
                        select(MemoryState).where(MemoryState.review_item_id == review_item.id)
                    )
                ).scalar_one()
                delayed = (now + timedelta(days=2)).isoformat(timespec="milliseconds")
                if ms_row.due < delayed:
                    ms_row.due = delayed
                    await db.flush()
            cp = await ksession.load_checkpoint(db, session.id) or {}
            if cp.get("skill_id") == a.skill_id and cp.get("hint_level"):
                await ksession.save_checkpoint(db, session, {**cp, "hint_level": 0}, commit=False)
            await competency.refresh(db, learner_id, a.skill_id, now=now, commit=False)
            mastery = await competency.mastery(db, learner_id, a.skill_id)
            ms = (
                await db.execute(
                    select(MemoryState).where(MemoryState.review_item_id == review_item.id)
                )
            ).scalar_one()
            calibration = _calibration(req.confidence_pre, score)
            completed = AttemptResult(
                attempt_id=attempt.id,
                assessment_id=a.id,
                skill_id=a.skill_id,
                kind=a.kind,
                dimension=dimension,
                correct=correct,
                score=score,
                criterion_results=result.criterion_results,
                misconception=result.misconception,
                confidence=result.confidence,
                grader_level=route_label,
                feedback=result.feedback,
                next_step=result.next_step,
                confidence_pre=req.confidence_pre,
                calibration=calibration,
                review={
                    "item_id": review_item.id,
                    "due": ms.due,
                    "state": ms.state,
                    "stability": ms.stability,
                },
                mastery=mastery,
            )
            if self.request_claim_id is not None:
                durable_result = completed.model_dump(mode="json")
                durable_result["_assessment_history_v1"] = feedback_snapshot(
                    completed,
                    req,
                    learner_id=learner_id,
                    question=question_snapshot,
                    area_id=node.area_id if node else None,
                    course_label=node.course if node else None,
                )
                await workspace_requests.complete(
                    db,
                    learner_id,
                    self.request_claim_id,
                    durable_result,
                    commit=False,
                )
                await assessment_executions.mark_completed(db, learner_id, self.request_claim_id)
            # A commit error may mean acknowledgement was lost after success.
            self.execution.learning_commit_started = True
            await db.commit()
        except BaseException:
            await db.rollback()
            raise
        # Searchable feedback is recoverable independently after learning state is durable.
        return await save_feedback(
            db,
            completed,
            req,
            learner_id=learner_id,
            question=question_snapshot,
            area_id=node.area_id if node else None,
            course_label=node.course if node else None,
            recovery=self.recovery,
        )


def _calibration(confidence_pre: int | None, score: float) -> str:
    """Describes the estimate, never the person."""
    if confidence_pre is None:
        return "confidence not supplied"
    expected = (confidence_pre - 1) / 4
    gap = expected - score
    if abs(gap) <= 0.25:
        return "estimate close to result"
    return "estimate higher than result" if gap > 0 else "estimate lower than result"
