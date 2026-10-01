"""Best-effort private indexing after HTTP delivery, separate from request state."""

import logging

from fastapi import BackgroundTasks, Request

from app.core.config import Settings
from app.orchestrator.answer_index import populate


def schedule_index(
    request: Request, background: BackgroundTasks, settings: Settings, learner_id: str
) -> None:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        return

    async def index_saved() -> None:
        try:
            async with factory() as db:
                await populate(db, settings, learner_id, limit=16)
        except Exception as exc:  # noqa: BLE001 — optional job cannot invalidate a delivered answer
            logging.getLogger(__name__).warning(
                "Answer indexing unavailable: %s", type(exc).__name__
            )

    background.add_task(index_saved)
