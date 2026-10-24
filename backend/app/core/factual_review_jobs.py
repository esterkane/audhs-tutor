"""Bounded periodic reviews of accepted material, sharing the app budget lock."""

import asyncio
import logging

from fastapi import FastAPI
from sqlalchemy import select

from app.db.base import utcnow_iso
from app.db.models import CurriculumDraft, KnowledgeReview
from app.kernel import preferences
from app.models_ai.budget import Budget
from app.models_ai.gateway import ModelGateway
from app.models_ai.routing import Router
from app.orchestrator.knowledge_reviews import run


async def tick(app: FastAPI) -> None:
    settings = app.state.settings
    if not settings.read_authoring_key():
        return
    async with app.state.session_factory() as db:
        due = list(
            (
                await db.scalars(
                    select(KnowledgeReview)
                    .join(CurriculumDraft, CurriculumDraft.id == KnowledgeReview.draft_id)
                    .where(
                        KnowledgeReview.enabled.is_(True),
                        KnowledgeReview.next_due_at <= utcnow_iso(),
                        CurriculumDraft.status == "published",
                    )
                    .order_by(KnowledgeReview.next_due_at)
                    .limit(3)
                )
            ).all()
        )
        for row in due:
            values = await preferences.get_all(db, row.learner_id)
            if not values["authoring.enabled"] or int(values["authoring.daily_budget_cents"]) <= 0:
                continue
            gateway = ModelGateway(
                db,
                Router(settings.routing_profile),
                app.state.providers,
                Budget(settings.daily_budget_usd, lock=app.state.budget_lock),
            )
            try:
                await run(db, gateway, settings, row.learner_id, row.draft_id, manual=False)
            except Exception:
                await db.rollback()
                logging.getLogger(__name__).warning("Scheduled factual review deferred")


async def worker(app: FastAPI) -> None:
    await asyncio.sleep(5)
    while True:
        try:
            await tick(app)
        except Exception:
            logging.getLogger(__name__).warning("Factual review scheduler deferred")
        await asyncio.sleep(300)
