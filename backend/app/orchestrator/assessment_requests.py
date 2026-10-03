"""Durable grading claims; unresolved work is never automatically graded again."""

from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.answer_recovery import AnswerRecovery
from app.db import workspace_requests
from app.db.models import TutorAnswer, WorkspaceRequest
from app.kernel.session import get_owned
from app.models_ai.gateway import ModelGateway
from app.orchestrator import assessment_content
from app.orchestrator.grader import Grader
from app.schemas.grading import AttemptRequest, AttemptResult


class AssessmentRequestState(BaseModel):
    status: Literal["not_found", "unresolved", "completed"]
    result: AttemptResult | None = None


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
    return await Grader(db, gateway, recovery=recovery, request_claim_id=claim_id).grade(body)


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
        return AssessmentRequestState(status="unresolved")
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
