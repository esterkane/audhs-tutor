"""Session-independent questions. Never creates a Session or learning evidence."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query
from fastapi.responses import StreamingResponse

from app.api.answers import summary
from app.api.deps import DB, Gateway, Learner, SettingsDep
from app.api.sse import stream_reply
from app.db import answer_suggestions
from app.orchestrator import ask
from app.schemas.answers import AnswerPage
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


@router.get(
    "/suggestions",
    response_model=AnswerPage,
    summary="Find local saved questions with source and feedback context",
)
async def suggestions(
    db: DB,
    learner: Learner,
    q: Annotated[str, Query(max_length=200)] = "",
    area_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> AnswerPage:
    rows = await answer_suggestions.ranked(db, learner.id, q, area_id, limit)
    items = []
    for row, source_check, reason in rows:
        item = summary(row)
        item.source_check = source_check
        item.suggestion_reason = reason
        items.append(item)
    return AnswerPage(items=items)
