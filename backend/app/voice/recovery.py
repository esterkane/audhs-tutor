"""Voice terminal lookup over the existing private request ledger; no model or audio calls."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WorkspaceRequest
from app.kernel.session import get_owned
from app.schemas.voice import VoiceResultOut


def key(request_id: str) -> str:
    return f"voice:{request_id}"


async def lookup(
    db: AsyncSession, learner_id: str, session_id: str, request_id: str
) -> VoiceResultOut:
    await get_owned(db, session_id, learner_id)
    row = await db.scalar(
        select(WorkspaceRequest).where(
            WorkspaceRequest.learner_id == learner_id,
            WorkspaceRequest.session_id == session_id,
            WorkspaceRequest.request_key == key(request_id),
        )
    )
    if row is None:
        result = VoiceResultOut(request_id=request_id, status="not_found")
    elif row.response_json is None:
        result = VoiceResultOut(request_id=request_id, status="unresolved")
    else:
        result = VoiceResultOut.model_validate(row.response_json)
    await db.commit()
    return result
