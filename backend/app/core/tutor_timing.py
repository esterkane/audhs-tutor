"""Content-free Session stream diagnostics; timestamps are server elapsed time, not paint."""

import json
import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass, field

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("uvicorn.error.tutor_timing")


@dataclass
class Timing:
    started: float = field(default_factory=lambda: time.perf_counter())
    marks: dict[str, int] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        # First occurrence only: first text must not become last text.
        if name not in self.marks:
            self.marks[name] = max(0, int((time.perf_counter() - self.started) * 1000))


_current: ContextVar[Timing | None] = ContextVar("tutor_timing", default=None)


def mark(name: str) -> None:
    timing = _current.get()
    if timing is not None:
        timing.mark(name)


class TutorTimingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") != "/api/tutor/stream":
            await self.app(scope, receive, send)
            return
        timing = Timing()
        token = _current.set(timing)
        status: int | None = None
        completed = False

        async def timed_send(message: Message) -> None:
            nonlocal status, completed
            await send(message)
            if message["type"] == "http.response.start":
                status = message["status"]
                timing.mark("headers_sent")
            elif message["type"] == "http.response.body" and not message.get("more_body", False):
                completed = True
                timing.mark("body_sent")

        try:
            await self.app(scope, receive, timed_send)
        finally:
            _current.reset(token)
            # No request text, URLs, headers, source IDs, learner IDs or model output.
            # Body completion excludes response background jobs; no-body is not success.
            logger.info(
                "tutor_timing %s",
                json.dumps(
                    {
                        "version": 1,
                        "scope": "server_request",
                        "status": status,
                        "body_completed": completed,
                        "marks_ms": timing.marks,
                    },
                    sort_keys=True,
                ),
            )
