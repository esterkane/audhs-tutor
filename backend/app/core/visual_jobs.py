"""Process handles for durable visual requests; SQLite remains authoritative."""

import asyncio
import logging

from starlette.applications import Starlette

from app.models_ai.budget import Budget
from app.models_ai.gateway import ModelGateway
from app.models_ai.routing import Router
from app.orchestrator.visual_generation import generate

log = logging.getLogger(__name__)


class VisualJobs:
    def __init__(self, app: Starlette):
        self.app = app
        self.tasks: dict[tuple[str, str], asyncio.Task[None]] = {}
        self.closing = False

    def start(self, owner: str, identity: str, budget: Budget) -> None:
        key = (owner, identity)
        if self.closing or key in self.tasks:
            return
        task = asyncio.create_task(self._run(owner, identity, budget))
        self.tasks[key] = task
        task.add_done_callback(lambda _: self.tasks.pop(key, None))

    async def _run(self, owner: str, identity: str, budget: Budget) -> None:
        settings = self.app.state.settings
        try:
            async with self.app.state.session_factory() as db:
                gateway = ModelGateway(
                    db, Router(settings.routing_profile), self.app.state.providers, budget
                )
                await generate(
                    self.app.state.session_factory,
                    gateway,
                    owner,
                    identity,
                    quarantine_below_trust=settings.quarantine_below_trust,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            # Error messages and raw model output may contain private material.
            log.warning("Visual worker ended without a result: %s", identity)

    def stop(self, owner: str, identity: str) -> None:
        task = self.tasks.get((owner, identity))
        if task is not None:
            task.cancel()

    async def close(self) -> None:
        self.closing = True
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
