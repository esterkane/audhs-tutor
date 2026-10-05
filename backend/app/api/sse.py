import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import suppress
from typing import Any

import anyio
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.errors import AppError


def sse(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


def stream_reply(
    produce: Callable[[Callable[[str], Awaitable[None]]], Awaitable[BaseModel]],
    *,
    background: BackgroundTasks | None = None,
) -> StreamingResponse:
    """Bounded preview transport; only a completed producer result is authoritative."""

    async def generate() -> AsyncIterator[bytes]:
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue(maxsize=32)

        async def token(text: str) -> None:
            await queue.put(("token", {"text": text}))

        async def work() -> None:
            try:
                reply = await produce(token)
                await queue.put(("done", reply.model_dump(mode="json")))
            except AppError as exc:
                await queue.put(("error", {"code": exc.code, "message": exc.message}))
            except Exception:
                logging.getLogger(__name__).exception("Tutor reply stream failed")
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
