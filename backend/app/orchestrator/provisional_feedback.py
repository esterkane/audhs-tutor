"""Atomic advisory persistence foundation; production routing is not connected yet."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import assessment_executions, workspace_requests
from app.db.base import new_id
from app.db.models import ProvisionalFeedback, WorkspaceRequest
from app.orchestrator import assessment_content
from app.schemas.grading import AttemptRequest, GradeResult
from app.schemas.provisional_feedback import (
    PROVISIONAL_POLICY,
    ProvisionalCriterionFeedback,
    ProvisionalFeedbackResult,
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
        payload = body.model_dump(mode="json")
        if body.revision_of_attempt_id is None:
            payload.pop("revision_of_attempt_id", None)
        if body.content_version is None:
            payload.pop("content_version", None)
        if (
            body.session_id != claim.session_id
            or workspace_requests.request_fingerprint(payload) != claim.fingerprint
        ):
            raise AppError("request_conflict", "The saved answer cannot be verified.", 409)
        # Revision lineage needs its own provisional ID contract before routing is enabled.
        if body.revision_of_attempt_id is not None:
            raise AppError(
                "revision_unavailable", "Provisional revision integration is pending.", 409
            )
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
        outcome = ProvisionalFeedbackResult(
            feedback_id=new_id(),
            assessment_id=body.assessment_id,
            session_id=body.session_id,
            skill_id=content["skill_id"],
            content_version=assessment_content.token(content),
            feedback=result.feedback,
            next_step=result.next_step,
            model_route=str(raw["level"]),
            criterion_feedback=[
                ProvisionalCriterionFeedback(
                    criterion=c.criterion,
                    observation=(
                        "Model suggests this is addressed. "
                        if c.passed
                        else "Model suggests more explanation is needed. "
                    )
                    + c.evidence,
                )
                for c in result.criterion_results
            ],
        )
        db.add(
            ProvisionalFeedback(
                id=outcome.feedback_id,
                learner_id=learner_id,
                claim_id=claim_id,
                session_id=body.session_id,
                assessment_id=body.assessment_id,
                policy_version=PROVISIONAL_POLICY,
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
        await workspace_requests.complete(
            db, learner_id, claim_id, outcome.model_dump(mode="json"), commit=False
        )
        await assessment_executions.mark_completed(db, learner_id, claim_id)
        await db.commit()
        return outcome
    except BaseException:
        await db.rollback()
        raise
