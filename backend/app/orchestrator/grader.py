"""Hierarchical grader (ADR-0009): deterministic → rubric checks → local LLM → hosted.

Every attempt produces: an assessment_attempt row, `attempted` + `graded` events, one
competency_evidence row (via the kernel, which emits `evidenced`), a competency refresh, and an
FSRS review of the item (via the kernel, which emits `reviewed`). Feedback is literal and specific.
"""

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventWriter, Verb
from app.db.models import Assessment, AssessmentAttempt, AssessmentRubric, MemoryState, Session
from app.kernel import competency, memory
from app.kernel import session as ksession
from app.models_ai.gateway import GatewayError, ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.models_ai.routing import NoModelReady
from app.orchestrator import prompts
from app.orchestrator.context import escape_data, learner_answer_block
from app.schemas.common import ActivityType, ObjectType
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
    return AssessmentView(
        id=a.id,
        skill_id=a.skill_id,
        kind=a.kind,
        question=item["prompt"],
        criteria=list(item.get("criteria", [])) if a.kind.startswith("challenge_") else None,
    )


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
    """Level 2: keyword rubric. Confident only when the answer is clearly complete or clearly empty."""
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
    n_pass = sum(1 for r in results if r.passed)
    if not results:
        conf = 0.0  # no rubric: nothing to check deterministically, force the LLM level
    elif n_pass == len(results):
        conf = 0.75
    elif n_pass == 0 and len(answer.split()) < 12:
        conf = 0.8
    else:
        conf = 0.35  # partial keyword overlap: a keyword match is not understanding; ask the LLM
    missing = [r.criterion for r in results if not r.passed]
    feedback = (
        "Your answer covers every rubric point."
        if not missing
        else f"Missing or unclear: {'; '.join(missing)}."
    )
    return GradeResult(
        criterion_results=results,
        confidence=conf,
        feedback=feedback,
        next_step="Next: add the missing point in one sentence.",
    )


class Grader:
    def __init__(self, db: AsyncSession, gateway: ModelGateway) -> None:
        self.db = db
        self.gateway = gateway

    async def next_item(self, learner_id: str, skill_id: str) -> Assessment | None:
        """Rotate kinds (mcq → cloze → explain_back); prefer items never attempted, then the oldest attempt."""
        items = list(
            (
                await self.db.execute(select(Assessment).where(Assessment.skill_id == skill_id))
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
        if not isinstance(result, GradeResult):
            return None
        # keep the rubric's criterion wording even if the model paraphrased
        for c, name in zip(result.criterion_results, criteria, strict=False):
            c.criterion = name
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
        item = a.item_json
        correct: bool | None
        rubric_version = None
        if a.kind == "mcq":
            result, correct = grade_mcq(item, req.answer)
            level = "deterministic"
        elif a.kind == "cloze":
            result, correct = grade_cloze(item, req.answer)
            level = "deterministic"
        else:
            rubric_row = await db.get(AssessmentRubric, a.rubric_id) if a.rubric_id else None
            criteria: list[dict[str, Any]] = rubric_row.criteria_json if rubric_row else []
            rubric_version = rubric_row.version if rubric_row else None
            result = rubric_checks(criteria, req.answer)
            level = "rubric"
            is_challenge = a.kind.startswith("challenge_")
            reference = str(item.get("hidden_key")) if is_challenge else None
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
            correct = None if 0.0 < result.score < 1.0 else result.score == 1.0

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
            grader_route=level,
            correct=correct,
            latency_ms=req.latency_ms,
            hint_count=req.hint_count,
        )
        db.add(attempt)
        await db.commit()

        events = EventWriter(db, ksession.event_context(session, activity=ActivityType.RETRIEVAL))
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
        )
        await events.emit(
            Verb.GRADED,
            ObjectType.ITEM,
            a.id,
            result={
                "criterion_results": [
                    {"criterion": c.criterion, "passed": c.passed} for c in result.criterion_results
                ],
                "score": score,
                "misconception": result.misconception,
                "confidence": result.confidence,
                "feedback_len": len(result.feedback),
            },
            context={
                "grader_level": level,
                "prompt_version": prompts.GRADER_VERSION if level in ("local", "hosted") else None,
                "rubric_version": rubric_version,
            },
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
        )
        review_item, _ = await memory.ensure_item(
            db, learner_id, a.skill_id, a.kind, {"ref": a.id, "assessment_id": a.id}, now=now
        )
        rating = memory.rating_from_score(score, hint_count=req.hint_count)
        if (
            level == "rubric"
        ):  # keyword overlap is not confirmed understanding: never the longest interval
            rating = min(rating, memory.Rating.Good)
        await memory.review(
            db,
            learner_id,
            review_item.id,
            int(rating),
            now=now,
            latency_ms=req.latency_ms,
            events=events,
        )
        if a.kind.startswith("challenge_"):
            # every challenge ends with a delayed item (ADR-0003): never earlier than +2 days
            from datetime import timedelta

            ms_row = (
                await db.execute(
                    select(MemoryState).where(MemoryState.review_item_id == review_item.id)
                )
            ).scalar_one()
            delayed = (now + timedelta(days=2)).isoformat(timespec="milliseconds")
            if ms_row.due < delayed:
                ms_row.due = delayed
                await db.commit()
        cp = await ksession.load_checkpoint(db, session.id) or {}
        if cp.get("skill_id") == a.skill_id and cp.get("hint_level"):
            await ksession.save_checkpoint(db, session, {**cp, "hint_level": 0})
        await competency.refresh(db, learner_id, a.skill_id, now=now)
        mastery = await competency.mastery(db, learner_id, a.skill_id)
        ms = (
            await db.execute(
                select(MemoryState).where(MemoryState.review_item_id == review_item.id)
            )
        ).scalar_one()
        calibration = _calibration(req.confidence_pre, score)
        return AttemptResult(
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
            grader_level=level,
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


def _calibration(confidence_pre: int, score: float) -> str:
    """Describes the estimate, never the person."""
    expected = (confidence_pre - 1) / 4
    gap = expected - score
    if abs(gap) <= 0.25:
        return "estimate close to result"
    return "estimate higher than result" if gap > 0 else "estimate lower than result"
