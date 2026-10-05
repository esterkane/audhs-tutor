import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import suppress
from typing import Annotated, Any
from uuid import UUID

import anyio
import httpx
from fastapi import APIRouter, BackgroundTasks, Header, Request
from fastapi.responses import StreamingResponse

from app.api.answer_jobs import schedule_index
from app.api.deps import DB, Gateway, Learner, SettingsDep, get_repo
from app.api.sse import sse
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

    async def generate() -> AsyncIterator[bytes]:
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue(maxsize=32)

        async def token(text: str) -> None:
            await queue.put(("token", {"text": text}))

        async def work() -> None:
            try:
                reply = await _answer(
                    body,
                    db,
                    learner,
                    gateway,
                    settings,
                    request,
                    background,
                    idempotency_key,
                    token,
                )
                await queue.put(("done", reply.model_dump(mode="json")))
            except AppError as exc:
                await queue.put(("error", {"code": exc.code, "message": exc.message}))
            except Exception:
                logging.getLogger(__name__).exception("Workspace stream failed")
                await queue.put(
                    (
                        "error",
                        {
                            "code": "tutor_failed",
                            "message": (
                                "The reply could not finish. Keep received text and use request recovery; "
                                "no automatic retry was made."
                            ),
                        },
                    )
                )

        task = asyncio.create_task(work())
        try:
            while True:
                kind, data = await queue.get()
                yield sse(kind, data)
                if kind in {"done", "error"}:
                    break
        finally:
            # Uvicorn/Starlette's disconnect scope is already cancelled here. Shield the
            # join so the worker can finish its model-accounting cleanup after one cancel.
            with anyio.CancelScope(shield=True):
                if not task.done():
                    task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        background=background,
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
