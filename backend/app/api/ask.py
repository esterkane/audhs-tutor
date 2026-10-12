"""Session-independent questions. Never creates a Session or learning evidence."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from app.api.deps import DB, Gateway, Learner, SettingsDep
from app.api.sse import stream_reply
from app.orchestrator import ask
from app.schemas.ask import AskQuestion, AskReply

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskReply, summary="Ask a question without a learning session")
async def question(
    body: AskQuestion,
    db: DB,
    gateway: Gateway,
    learner: Learner,
    settings: SettingsDep,
    idempotency_key: Annotated[UUID, Header()],
) -> AskReply:
    return await ask.respond(
        db,
        gateway,
        learner.id,
        body,
        str(idempotency_key),
        quarantine_below_trust=settings.quarantine_below_trust,
    )


@router.post("/stream", summary="Stream an independent explanation and its saved result")
async def question_stream(
    body: AskQuestion,
    db: DB,
    gateway: Gateway,
    learner: Learner,
    settings: SettingsDep,
    idempotency_key: Annotated[UUID, Header()],
) -> StreamingResponse:
    learner_id = learner.id

    async def produce(on_token: Callable[[str], Awaitable[None]]) -> AskReply:
        return await ask.respond(
            db,
            gateway,
            learner_id,
            body,
            str(idempotency_key),
            on_token,
            quarantine_below_trust=settings.quarantine_below_trust,
        )

    return stream_reply(produce)
