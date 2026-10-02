"""Durable grading claims; unresolved work is never automatically graded again."""

from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.answer_recovery import AnswerRecovery
from app.db import workspace_requests
from app.db.models import WorkspaceRequest
from app.kernel.session import get_owned
from app.models_ai.gateway import ModelGateway
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
    claim_id = None
    if identity is not None:
        claim_id, saved = await workspace_requests.claim(
            db, learner_id, body.session_id, request_key(identity), body.model_dump(mode="json")
        )
        if saved is not None:
            return AttemptResult.model_validate(saved)
    result = await Grader(db, gateway, recovery=recovery).grade(body)
    if claim_id is not None:
        await workspace_requests.complete(db, learner_id, claim_id, result.model_dump(mode="json"))
    return result


async def lookup(
    db: AsyncSession, learner_id: str, session_id: str, identity: str
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
        status="completed", result=AttemptResult.model_validate(row.response_json)
    )
