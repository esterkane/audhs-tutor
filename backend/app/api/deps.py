"""Request-scoped dependencies. Providers and the retrieval repo live on app.state (set in lifespan
or overridden by tests); nothing is a module singleton."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import LearnerProfile
from app.db.session import get_db
from app.kernel.learner import get_or_create_owner
from app.knowledge.repository import RetrievalRepository
from app.models_ai.budget import Budget
from app.models_ai.gateway import ModelGateway
from app.models_ai.routing import Router

DB = Annotated[AsyncSession, Depends(get_db)]


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


async def get_learner(db: DB) -> LearnerProfile:
    return await get_or_create_owner(db)


Learner = Annotated[LearnerProfile, Depends(get_learner)]


def get_budget(request: Request, settings: SettingsDep) -> Budget:
    """One reservation lock per app process (app.state, never a module singleton)."""
    lock = getattr(request.app.state, "budget_lock", None)
    if lock is None:
        import asyncio

        lock = asyncio.Lock()
        request.app.state.budget_lock = lock
    return Budget(settings.daily_budget_usd, lock=lock)


BudgetDep = Annotated[Budget, Depends(get_budget)]


async def get_gateway(
    request: Request, db: DB, settings: SettingsDep, budget: BudgetDep
) -> ModelGateway:
    return ModelGateway(db, Router(settings.routing_profile), request.app.state.providers, budget)


Gateway = Annotated[ModelGateway, Depends(get_gateway)]


async def get_repo(request: Request, db: DB, settings: SettingsDep) -> RetrievalRepository:
    repo: RetrievalRepository | None = getattr(request.app.state, "repo", None)
    if repo is None:
        from app.knowledge.reindex import build_repo

        repo = await build_repo(db, settings)
        request.app.state.repo = repo
    return repo


Repo = Annotated[RetrievalRepository, Depends(get_repo)]
