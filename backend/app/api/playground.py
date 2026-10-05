import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, Request
from fastapi.responses import StreamingResponse

from app.api.answer_jobs import schedule_index
from app.api.deps import DB, Gateway, Learner, SettingsDep, get_repo
from app.api.sse import stream_reply
from app.core.errors import AppError
from app.db import workspace_requests
from app.models_ai.provider import ProviderError
from app.models_ai.routing import NoModelReady
from app.orchestrator import playground
from app.schemas.playground import PlaygroundReply, PlaygroundRequest

router = APIRouter(prefix="/playground", tags=["playground"])


@router.post(
    "/tutor",
    summary="Explain, hint or discuss a bounded coding workspace",
    response_model=PlaygroundReply,
)
async def tutor(
    body: PlaygroundRequest,
    db: DB,
    learner: Learner,
    gateway: Gateway,
    settings: SettingsDep,
    request: Request,
    background: BackgroundTasks,
    idempotency_key: Annotated[UUID | None, Header()] = None,
) -> PlaygroundReply:
    return await _answer(body, db, learner, gateway, settings, request, background, idempotency_key)


async def _answer(
    body: PlaygroundRequest,
    db: DB,
    learner: Learner,
    gateway: Gateway,
    settings: SettingsDep,
    request: Request,
    background: BackgroundTasks,
    idempotency_key: UUID | None,
    on_token: Callable[[str], Awaitable[None]] | None = None,
) -> PlaygroundReply:
    learner_id = learner.id

    async def validate_origin() -> None:
        await playground.validate_lesson_origin(db, learner_id, body)

    identity = None
    if idempotency_key is not None:
        identity, saved = await workspace_requests.claim(
            db,
            learner_id,
            body.session_id,
            str(idempotency_key),
            body.model_dump(mode="json"),
            validate_new=validate_origin if body.lesson_origin else None,
        )
        if saved is not None:
            return PlaygroundReply.model_validate(saved)
    repo = None
    if body.lesson_origin and body.intent != "check_bins":
        try:
            repo = await asyncio.wait_for(get_repo(request, db, settings), timeout=5.0)
        except (httpx.HTTPError, ProviderError, NoModelReady, TimeoutError, ValueError) as exc:
            logging.getLogger(__name__).warning(
                "Lesson repository unavailable: %s", type(exc).__name__
            )
    reply = await playground.respond(
        db,
        gateway,
        learner_id,
        body,
        settings=settings,
        recovery=request.app.state.answer_recovery,
        repo=repo,
        on_token=on_token,
    )
    if identity is not None:
        await workspace_requests.complete(db, learner_id, identity, reply.model_dump(mode="json"))
    if reply.answer_id and not reply.reused:
        schedule_index(request, background, settings, learner_id)
    return reply


@router.post(
    "/tutor/stream", summary="Stream unfinished workspace text, then its authoritative reply"
)
async def tutor_stream(
    body: PlaygroundRequest,
    db: DB,
    learner: Learner,
    gateway: Gateway,
    settings: SettingsDep,
    request: Request,
    background: BackgroundTasks,
    idempotency_key: Annotated[UUID | None, Header()] = None,
) -> StreamingResponse:
    if body.intent not in {"explain", "hint", "chat"}:
        raise AppError("buffered_intent", "Use the checked response endpoint for this action.", 422)

    async def produce(on_token: Callable[[str], Awaitable[None]]) -> PlaygroundReply:
        return await _answer(
            body, db, learner, gateway, settings, request, background, idempotency_key, on_token
        )

    return stream_reply(produce, background=background)
