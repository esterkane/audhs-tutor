"""Pinned project host integration; optional local stack never prevents core app startup."""

import importlib
import sys
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import DB, Learner
from app.integrations.supabase_bridge import LocalProjectClient, LocalProjectEmbedder
from app.kernel import preferences

PROJECT_REPOSITORY = "https://github.com/esterkane/kanguroo-supabase-tutor"
PROJECT_REVISION = "5786968dfde6b9f1a4d5b157977b92e16d36ad69"
PROJECT_ROOT = Path(__file__).resolve().parents[3] / "integrations" / "supabase-tutor"


def project_module() -> Any:
    if not (PROJECT_ROOT / "kaenguru_tutor" / "__init__.py").is_file():
        raise ImportError("The pinned Supabase project source snapshot is missing.")
    value = str(PROJECT_ROOT)
    if value not in sys.path:
        sys.path.insert(0, value)
    return importlib.import_module("kaenguru_tutor")


def mount(app: Any) -> None:
    app.state.tutor = None
    app.state.supabase_project_error = "Local Supabase project is not configured."
    try:
        project = project_module()
        app.include_router(
            project.router, prefix="/api/supabase-project", tags=["supabase-project"]
        )
    except ImportError:
        return


async def open_project(app: Any) -> None:
    settings = app.state.settings
    if not settings.supabase_project_db_url or not settings.supabase_project_user_id:
        return
    service = None
    try:
        project = project_module()
        embedder = LocalProjectEmbedder(app.state.session_factory, app.state.providers, settings)
        service = project.build_service(
            project.HostConfig(
                db_url=settings.supabase_project_db_url,
                supabase_url=settings.supabase_project_url,
                user_id=UUID(settings.supabase_project_user_id),
                anthropic_api_key=None,
                extra={"embedder": embedder},
            )
        )
        embedder.project_pool = service.app_pool
        import asyncio

        from app.models_ai.budget import Budget

        if getattr(app.state, "budget_lock", None) is None:
            app.state.budget_lock = asyncio.Lock()
        service.anthropic = LocalProjectClient(
            app.state.session_factory,
            app.state.providers,
            settings,
            Budget(settings.daily_budget_usd, lock=app.state.budget_lock),
        )
        from app.integrations.supabase_reviewed import ReviewedOrchestrator

        original_orchestrator = service.orchestrator
        service.orchestrator = lambda user_id=None: ReviewedOrchestrator(
            original_orchestrator(user_id)
        )
        await service.open()
        await service.app_pool.wait(timeout=5)
        await service.lab_pool.wait(timeout=5)
        app.state.tutor = service
        app.state.supabase_project_error = None
    except Exception as error:
        if service is not None:
            try:
                await service.close()
            except Exception:
                pass  # Preserve original safe setup error without leaking a private DSN.
        app.state.tutor = None
        app.state.supabase_project_error = (
            "Local Supabase project needs setup (" + type(error).__name__ + ")."
        )


async def close_project(app: Any) -> None:
    if app.state.tutor is not None:
        await app.state.tutor.close()


router = APIRouter(prefix="/learning-focus", tags=["learning-focus"])


class SupabaseProjectStatus(BaseModel):
    ready: bool
    user_id: str | None
    repository: str
    revision: str
    detail: str | None
    study_provider: str = "local"
    hosted_study_enabled: bool = False
    study_model: str = "openai-luna-study"


@router.get("/supabase", response_model=SupabaseProjectStatus)
async def status(request: Request, db: DB, learner: Learner) -> dict[str, Any]:
    settings = request.app.state.settings
    provider = await preferences.get(db, learner.id, "project.study_provider")
    return {
        "ready": request.app.state.tutor is not None,
        "user_id": settings.supabase_project_user_id
        if request.app.state.tutor is not None
        else None,
        "repository": PROJECT_REPOSITORY,
        "revision": PROJECT_REVISION,
        "detail": request.app.state.supabase_project_error,
        "study_provider": provider,
        "study_model": await preferences.get(db, learner.id, "project.study_model"),
        "hosted_study_enabled": provider in {"openai", "anthropic"},
    }


class ProjectStudyChoice(BaseModel):
    provider: Literal["local", "openai"]
    model: Literal["openai-luna-study", "openai-sol-study"] = "openai-luna-study"


@router.put("/supabase/study", response_model=SupabaseProjectStatus)
async def set_study(
    choice: ProjectStudyChoice, request: Request, db: DB, learner: Learner
) -> dict[str, Any]:
    """Change project explanation routing atomically; no inference or history changes."""
    from app.models_ai.budget import Budget
    from app.orchestrator.project_study_gateway import choose_project_study

    if choice.provider == "openai":
        from app.models_ai import registry

        await registry.seed_defaults(db, installed_ollama_tags=set())
    async with db.begin_nested():
        await preferences.set_pref(
            db, learner.id, "project.study_provider", choice.provider, commit=False
        )
        if choice.provider == "openai":
            await preferences.set_pref(
                db, learner.id, "project.study_model", choice.model, commit=False
            )
            await choose_project_study(
                db, request.app.state.settings, learner.id, request.app.state.providers, Budget(0)
            )
    await db.commit()
    return await status(request, db, learner)
