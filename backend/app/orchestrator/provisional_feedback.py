"""Atomic advisory persistence for model-checked free-text feedback."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import assessment_executions, workspace_requests
from app.db.answers import save_completed
from app.db.base import new_id
from app.db.events import EventWriter, Verb
from app.db.models import ProvisionalFeedback, SkillNode, WorkspaceRequest
from app.kernel import session as ksession
from app.orchestrator import assessment_content, assessment_revisions
from app.orchestrator.assessment_answers import feedback_snapshot
from app.schemas.common import ActivityType, Domain, ObjectType
from app.schemas.grading import AssessmentView, AttemptRequest, GradeResult
from app.schemas.provisional_feedback import (
    PROVISIONAL_POLICY,
    ProvisionalCriterionFeedback,
    ProvisionalFeedbackResult,
)


def verified_excerpt(evidence: str, answer: str) -> str | None:
    """Remove only our known data wrapper, then require a verbatim learner excerpt."""
    quote = evidence.strip().strip('"“”').strip()
    opening, closing = "<learner_answer>", "</learner_answer>"
    if quote.startswith(opening) and quote.endswith(closing):
        quote = quote[len(opening) : -len(closing)].strip()
    if not quote or quote.casefold() == "absent" or quote not in answer:
        return None
    return quote


def addressed_summary(result: GradeResult, answer: str) -> tuple[str, str]:
    """Render consistent advisory feedback from complete, quoted rubric evidence.

    Do not alter criterion judgments or the preserved raw model output. Errors,
    omissions, misconceptions and unverified quotations retain specific model help.
    """
    original = result.feedback, result.next_step
    if (
        not result.criterion_results
        or any(not row.passed for row in result.criterion_results)
        or (result.misconception and result.misconception.strip())
    ):
        return original
    quotes = [verified_excerpt(row.evidence, answer) for row in result.criterion_results]
    if any(quote is None for quote in quotes):
        return original
    quote = quotes[0]
    assert quote is not None
    if len(quote) > 240:
        quote = quote[:237].rstrip() + "…"
    return (
        f"The model found evidence for each listed criterion. For example, you wrote: “{quote}”.",
        "Continue with this lesson, or try another question on the same idea.",
    )


async def get_owned(db: AsyncSession, learner_id: str, feedback_id: str) -> ProvisionalFeedback:
    row = await db.scalar(
        select(ProvisionalFeedback).where(
            ProvisionalFeedback.id == feedback_id,
            ProvisionalFeedback.learner_id == learner_id,
        )
    )
    if row is None:
        raise AppError("not_found", "Feedback not found.", 404)
    return row


async def persist_staged(
    db: AsyncSession, learner_id: str, claim_id: str
) -> ProvisionalFeedbackResult:
    """Commit one staged model result without any learning/scheduling writes.

    Owns its short transaction; callers must finish prior writes before entering.
    Existing assessed claims are deliberately not interpreted by this function.
    """
    await db.commit()
    try:
        await db.execute(
            update(WorkspaceRequest)
            .where(WorkspaceRequest.id == claim_id, WorkspaceRequest.learner_id == learner_id)
            .values(fingerprint=WorkspaceRequest.fingerprint)
        )
        claim = await db.scalar(
            select(WorkspaceRequest)
            .where(WorkspaceRequest.id == claim_id, WorkspaceRequest.learner_id == learner_id)
            .execution_options(populate_existing=True)
        )
        if claim is None or not claim.request_key.startswith("assessment:"):
            raise AppError("not_found", "Assessment request not found.", 404)
        if claim.response_json is not None:
            saved = ProvisionalFeedbackResult.model_validate(claim.response_json)
            record = await get_owned(db, learner_id, saved.feedback_id)
            if record.claim_id != claim_id or record.outcome_json != saved.model_dump(mode="json"):
                raise AppError("request_conflict", "The saved feedback cannot be verified.", 409)
            await db.commit()
            return saved
        staged = await assessment_executions.get_owned(db, learner_id, claim_id)
        if staged is None or staged.schema_version != 1 or staged.phase != "grade_ready":
            raise AppError("request_unresolved", "No saved model feedback is available.", 409)
        body = AttemptRequest.model_validate(staged.request_json)
        payload = body.identity_payload()
        if (
            body.session_id != claim.session_id
            or workspace_requests.request_fingerprint(payload) != claim.fingerprint
        ):
            raise AppError("request_conflict", "The saved answer cannot be verified.", 409)
        raw = staged.grade_json or {}
        if raw.get("version") != 1 or raw.get("level") not in ("local", "hosted"):
            raise AppError("request_conflict", "This is not staged model feedback.", 409)
        result = GradeResult.model_validate(raw.get("result"))
        content = await assessment_content.snapshot(db, body.assessment_id, learner_id)
        assessment_content.require_eligible(content)
        if assessment_content.recovery_fingerprint(content) != staged.content_fingerprint:
            raise AppError(
                "assessment_content_changed", "The saved feedback belongs to earlier content.", 409
            )
        if content["kind"] in ("mcq", "cloze", "code"):
            raise AppError(
                "request_conflict", "This task does not use provisional free-text feedback.", 409
            )
        await assessment_content.guard_write(db, body.assessment_id, content, learner_id)
        if body.revision_of_feedback_id is not None:
            await assessment_revisions.validate_provisional_root(
                db,
                learner_id=learner_id,
                session_id=body.session_id,
                assessment_id=body.assessment_id,
                root_feedback_id=body.revision_of_feedback_id,
                allow_ended=True,
            )
        previous_assessed = None
        if body.revision_of_feedback_id is None:
            previous_assessed = await assessment_revisions.resolve_root(
                db,
                learner_id=learner_id,
                session_id=body.session_id,
                assessment_id=body.assessment_id,
                content_fingerprint=staged.content_fingerprint,
                supplied_root=body.revision_of_attempt_id,
                allow_ended=True,
            )
        feedback, next_step = addressed_summary(result, body.answer)
        outcome = ProvisionalFeedbackResult(
            feedback_id=new_id(),
            previous_assessed_attempt_id=previous_assessed,
            revision_of_feedback_id=body.revision_of_feedback_id,
            assessment_id=body.assessment_id,
            session_id=body.session_id,
            skill_id=content["skill_id"],
            content_version=assessment_content.token(content),
            feedback=feedback,
            next_step=next_step,
            model_route=str(raw["level"]),
            criterion_feedback=[
                ProvisionalCriterionFeedback(
                    criterion=c.criterion,
                    observation=(
                        "Model suggests this is addressed. "
                        if c.passed
                        else "Model suggests more explanation is needed. "
                    )
                    + (verified_excerpt(c.evidence, body.answer) or c.evidence),
                )
                for c in result.criterion_results
            ],
        )
        node = await db.get(SkillNode, content["skill_id"])
        question = AssessmentView(
            id=body.assessment_id,
            skill_id=content["skill_id"],
            kind=content["kind"],
            question=content["item_json"]["prompt"],
            criteria=list(content["item_json"].get("criteria", []))
            if content["kind"].startswith("challenge_")
            else None,
        ).model_dump()
        saved_answer = await save_completed(
            db,
            **feedback_snapshot(
                outcome,
                body,
                learner_id=learner_id,
                question=question,
                area_id=node.area_id if node else None,
                course_label=node.course if node else None,
            ),
            commit=False,
        )
        outcome = outcome.model_copy(update={"answer_id": saved_answer.id})
        db.add(
            ProvisionalFeedback(
                id=outcome.feedback_id,
                learner_id=learner_id,
                claim_id=claim_id,
                session_id=body.session_id,
                assessment_id=body.assessment_id,
                policy_version=PROVISIONAL_POLICY,
                revision_of_feedback_id=body.revision_of_feedback_id,
                content_fingerprint=staged.content_fingerprint,
                answer=body.answer,
                binding_json={
                    "content": content,
                    "request": staged.request_json,
                    "task_review": staged.task_review_json,
                },
                model_output_json=raw,
                outcome_json=outcome.model_dump(mode="json"),
            )
        )
        await db.flush()
        session = await ksession.get(db, body.session_id)
        node = await db.get(SkillNode, content["skill_id"])
        domain = (
            Domain(node.domain)
            if node and node.domain in {d.value for d in Domain}
            else Domain.META
        )
        events = EventWriter(
            db, ksession.event_context(session, domain=domain, activity=ActivityType.RETRIEVAL)
        )
        await events.emit(
            Verb.PROVISIONAL_FEEDBACK_SAVED,
            ObjectType.ITEM,
            body.assessment_id,
            result={"feedback_len": len(outcome.feedback)},
            context={
                "feedback_id": outcome.feedback_id,
                "policy_version": PROVISIONAL_POLICY,
                "model_route": outcome.model_route,
                "node_id": outcome.skill_id,
            },
            commit=False,
        )
        await workspace_requests.complete(
            db, learner_id, claim_id, outcome.model_dump(mode="json"), commit=False
        )
        await assessment_executions.mark_completed(db, learner_id, claim_id)
        await db.commit()
        return outcome
    except BaseException:
        await db.rollback()
        raise
