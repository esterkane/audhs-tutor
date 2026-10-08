"""Durable grading claims; unresolved work is never automatically graded again."""

import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.answer_recovery import AnswerRecovery
from app.core.errors import AppError
from app.core.local_ownership import OwnershipUnavailable
from app.db import assessment_executions, workspace_requests
from app.db.models import TutorAnswer, WorkspaceRequest
from app.kernel.session import get_owned
from app.models_ai.gateway import ModelGateway
from app.orchestrator import assessment_content
from app.orchestrator.assessment_execution import AssessmentExecution
from app.orchestrator.assessment_guard import AssessmentGuard
from app.orchestrator.grader import Grader
from app.schemas.grading import AttemptRequest, AttemptResult, GradeResult

logger = logging.getLogger(__name__)


class AssessmentRequestState(BaseModel):
    status: Literal["not_found", "unresolved", "prepared_ready", "grade_ready", "completed"]
    result: AttemptResult | None = None
    saved_grade: GradeResult | None = None


def request_key(identity: str) -> str:
    return f"assessment:{identity}"


async def submit(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    body: AttemptRequest,
    recovery: AnswerRecovery,
    identity: str | None,
) -> AttemptResult:
    await get_owned(db, body.session_id, learner_id)

    async def validate() -> None:
        await assessment_content.validate_new(db, body.assessment_id, body.content_version)

    payload = body.model_dump(mode="json")
    if body.content_version is None:
        payload.pop("content_version", None)  # Preserve pre-version completed claim fingerprints.
    claim_id = None
    if identity is not None:
        claim_id, saved = await workspace_requests.claim(
            db, learner_id, body.session_id, request_key(identity), payload, validate_new=validate
        )
        if saved is not None:
            return await recovered_result(db, learner_id, saved, recovery)
    else:
        await validate()
    execution = AssessmentExecution()
    try:
        if claim_id is not None:
            url = db.get_bind().engine.url
            if (
                url.get_backend_name() == "sqlite"
                and url.database
                and url.database != ":memory:"
                and not url.query
            ):
                try:
                    execution.guard = AssessmentGuard.create(Path(url.database), claim_id)
                except (OwnershipUnavailable, OSError):
                    # Grading stays available without recovery proof on unsupported storage.
                    logger.warning("Assessment ownership unavailable; recovery remains unknown")
        return await Grader(
            db, gateway, recovery=recovery, request_claim_id=claim_id, execution=execution
        ).grade(body)
    except Exception:
        # Cancellation/process death and all post-gateway failures stay uncertain.
        # Only this invocation owns the new claim; legacy unresolved claims never
        # pass claim() above. Preserve the original error if cleanup also fails.
        if claim_id is not None and identity is not None and execution.can_release:
            try:
                await db.rollback()
                await workspace_requests.release_unstarted_assessment(
                    db, learner_id, body.session_id, request_key(identity), claim_id
                )
            except Exception:
                logger.exception("Could not release an unstarted assessment claim")
        raise
    finally:
        if execution.guard is not None:
            execution.guard.close()


async def lookup(
    db: AsyncSession,
    learner_id: str,
    session_id: str,
    identity: str,
    recovery: AnswerRecovery | None = None,
) -> AssessmentRequestState:
    await get_owned(db, session_id, learner_id)
    row = await db.scalar(
        select(WorkspaceRequest).where(
            WorkspaceRequest.learner_id == learner_id,
            WorkspaceRequest.session_id == session_id,
            WorkspaceRequest.request_key == request_key(identity),
        )
    )
    if row is None:
        return AssessmentRequestState(status="not_found")
    if row.response_json is None:
        execution = await assessment_executions.get_owned(db, learner_id, row.id)
        if execution and execution.phase == "grade_ready" and execution.schema_version == 1:
            staged = StagedGrade.model_validate(execution.grade_json)
            return AssessmentRequestState(status="grade_ready", saved_grade=staged.result)
        try:
            guard, _ = await _acquire_prepared(db, learner_id, session_id, row)
        except (AppError, OwnershipUnavailable, OSError, ValueError):
            return AssessmentRequestState(status="unresolved")
        else:
            guard.close()
            return AssessmentRequestState(status="prepared_ready")
    return AssessmentRequestState(
        status="completed",
        result=await recovered_result(db, learner_id, row.response_json, recovery),
    )


async def recovered_result(
    db: AsyncSession,
    learner_id: str,
    saved: dict[str, Any],
    recovery: AnswerRecovery | None,
) -> AttemptResult:
    """Read history status; reissue a save-only receipt from the durable original snapshot."""
    result = AttemptResult.model_validate(saved)
    snapshot = saved.get("_assessment_history_v1")
    if not isinstance(snapshot, dict):
        return result  # Older completed claims already contain their final result.
    answer = await db.scalar(
        select(TutorAnswer).where(
            TutorAnswer.learner_id == learner_id,
            TutorAnswer.turn_id == f"assessment:{result.attempt_id}",
        )
    )
    if answer is not None:
        return result.model_copy(
            update={"answer_id": answer.id, "save_error": None, "save_receipt": None}
        )
    if not str(snapshot.get("text", "")).strip():
        return result.model_copy(
            update={
                "save_error": "Grading finished without feedback text to save. Your grading result remains here."
            }
        )
    return result.model_copy(
        update={
            "save_error": (
                "Grading finished. Saving feedback to answer history is unconfirmed. "
                "Retry saving, not grading."
            ),
            "save_receipt": recovery.issue(snapshot) if recovery else None,
        }
    )


class StagedGrade(BaseModel):
    version: Literal[1]
    graded_at: AwareDatetime
    result: GradeResult
    correct: bool | None
    level: Literal["deterministic", "rubric", "local", "hosted"]
    rubric_version: int | None


async def finish(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    session_id: str,
    identity: str,
    recovery: AnswerRecovery,
) -> AttemptResult:
    """Explicitly save already graded work, including for an ended owned session."""
    await get_owned(db, session_id, learner_id)
    claim = await db.scalar(
        select(WorkspaceRequest).where(
            WorkspaceRequest.learner_id == learner_id,
            WorkspaceRequest.session_id == session_id,
            WorkspaceRequest.request_key == request_key(identity),
        )
    )
    if claim is None:
        raise AppError("not_found", "Assessment request not found.", 404)
    if claim.response_json is not None:
        return await recovered_result(db, learner_id, claim.response_json, recovery)
    execution = await assessment_executions.get_owned(db, learner_id, claim.id)
    if execution is None or execution.phase != "grade_ready" or execution.schema_version != 1:
        raise AppError(
            "request_unresolved", "No saved grade is available to finish. No model was called.", 409
        )
    staged = StagedGrade.model_validate(execution.grade_json)
    body = AttemptRequest.model_validate(execution.request_json)
    if body.session_id != session_id:
        raise AppError("request_conflict", "The saved request belongs to another session.", 409)
    content = await assessment_content.snapshot(db, body.assessment_id)
    if assessment_content.recovery_fingerprint(content) != execution.content_fingerprint:
        raise AppError(
            "assessment_content_changed",
            "The question changed. The saved grade is retained, but cannot update progress.",
            409,
        )
    return await Grader(db, gateway, recovery=recovery, request_claim_id=claim.id).apply_result(
        body,
        content,
        staged.result,
        correct=staged.correct,
        level=staged.level,
        rubric_version=staged.rubric_version,
        now=staged.graded_at,
    )


async def _acquire_prepared(
    db: AsyncSession, learner_id: str, session_id: str, claim: WorkspaceRequest
) -> tuple[AssessmentGuard, AttemptRequest]:
    """Conservative preflight shared by lookup and explicit continuation; no inference."""
    row = await assessment_executions.get_owned(db, learner_id, claim.id)
    if (
        row is None
        or row.schema_version != 1
        or row.phase != "prepared"
        or not isinstance(row.owner_json, dict)
    ):
        raise OwnershipUnavailable("No prepared ownership proof")
    receipt, claim_id = dict(row.owner_json), claim.id
    url = db.get_bind().engine.url
    if (
        url.get_backend_name() != "sqlite"
        or not url.database
        or url.database == ":memory:"
        or url.query
    ):
        raise OwnershipUnavailable("No local ownership proof")
    await db.commit()  # No stale read snapshot or long transaction around lock acquisition.
    guard = AssessmentGuard.acquire_prepared(Path(url.database), claim_id, receipt)
    if guard is None:
        raise OwnershipUnavailable("Submission is still owned")
    try:
        claim, row = await assessment_executions.lock_prepared(db, learner_id, claim_id, receipt)
        body = AttemptRequest.model_validate(row.request_json)
        if claim.session_id != session_id or body.session_id != session_id:
            raise AppError("request_conflict", "The saved request belongs to another session.", 409)
        payload = body.model_dump(mode="json")
        if body.content_version is None:
            payload.pop("content_version", None)
        if workspace_requests.request_fingerprint(payload) != claim.fingerprint:
            raise AppError("request_conflict", "The saved answer cannot be verified.", 409)
        session = await get_owned(db, session_id, learner_id)
        await db.refresh(session)
        if session.ended_at:
            raise AppError(
                "request_unresolved", "This session has ended. Your original answer is kept.", 409
            )
        content = await assessment_content.snapshot(db, body.assessment_id)
        if assessment_content.recovery_fingerprint(content) != row.content_fingerprint:
            raise AppError(
                "request_unresolved", "The question changed. Your original answer is kept.", 409
            )
        # Process-bound public tokens can rotate. Only verified stable private content
        # permits refreshing the in-memory token; original durable intent is untouched.
        body = body.model_copy(update={"content_version": assessment_content.token(content)})
        await db.commit()
        return guard, body
    except BaseException:
        try:
            await db.rollback()
        finally:
            guard.close()
        raise


async def continue_prepared(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    session_id: str,
    identity: str,
    recovery: AnswerRecovery,
) -> AttemptResult:
    """Explicit owner action; never resend ambiguous or already-started inference."""
    await get_owned(db, session_id, learner_id)
    claim = await db.scalar(
        select(WorkspaceRequest).where(
            WorkspaceRequest.learner_id == learner_id,
            WorkspaceRequest.session_id == session_id,
            WorkspaceRequest.request_key == request_key(identity),
        )
    )
    if claim is None:
        raise AppError("not_found", "Assessment request not found.", 404)
    if claim.response_json is not None:
        return await recovered_result(db, learner_id, claim.response_json, recovery)
    try:
        guard, body = await _acquire_prepared(db, learner_id, session_id, claim)
    except (OwnershipUnavailable, OSError, ValueError) as error:
        raise AppError(
            "request_unresolved",
            "This submission cannot safely continue. Check its saved result; your answer is kept.",
            409,
        ) from error
    try:
        return await Grader(
            db,
            gateway,
            recovery=recovery,
            request_claim_id=claim.id,
            execution=AssessmentExecution(guard=guard, prepared_continuation=True),
        ).grade(body)
    finally:
        # Even pre-inference failure retains the original claim and answer. Only an
        # explicit later continuation may run it; normal submit still returns409.
        guard.close()
