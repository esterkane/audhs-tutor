"""FastAPI entrypoint. `make dev` runs `uvicorn app.main:app`."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api import api_router
from app.core.answer_recovery import AnswerRecovery
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.tutor_timing import TutorTimingMiddleware
from app.core.visual_jobs import VisualJobs
from app.db.migrate import upgrade_to_head
from app.db.session import make_engine, make_session_factory
from app.models_ai.factory import build_providers
from app.notebooks.lab import NotebookLab


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.auto_migrate:
            upgrade_to_head(settings.sync_database_url)
        engine = make_engine(settings.database_url_resolved)
        app.state.engine = engine
        app.state.session_factory = make_session_factory(engine)
        from app.kernel.visual_generation import GenerationRequests

        await GenerationRequests(app.state.session_factory).interrupt_abandoned()
        if getattr(app.state, "providers", None) is None:
            app.state.providers = build_providers(settings)
        from app.integrations.supabase_project import close_project, open_project

        await open_project(app)
        try:
            from app.knowledge.ingest.recovery import reconcile_abandoned_runs

            await reconcile_abandoned_runs(app.state.session_factory)
            from app.core.factual_review_jobs import worker

            app.state.budget_lock = asyncio.Lock()
            review_task = asyncio.create_task(worker(app))
            try:
                yield
            finally:
                review_task.cancel()
                with suppress(asyncio.CancelledError):
                    await review_task
        finally:
            await close_project(app)
            await app.state.visual_jobs.close()
            await app.state.notebook_lab.close()
            task = getattr(app.state, "area_job_task", None)
            if task and not task.done():
                task.cancel()
                await task
            from app.knowledge.ingest.jobs import stop_all

            await stop_all(app)  # a running ingest is recorded `interrupted`, hence resumable
            repo = getattr(app.state, "repo", None)
            if repo is not None and hasattr(repo, "client"):
                await repo.client.close()
            await engine.dispose()

    app = FastAPI(title="AuDHS-Tutor", version="0.1.0", lifespan=lifespan)
    app.add_middleware(TutorTimingMiddleware)
    app.state.settings = settings
    app.state.visual_jobs = VisualJobs(app)
    app.state.answer_recovery = AnswerRecovery()
    app.state.providers = None
    app.state.repo = None
    app.state.notebook_lab = NotebookLab(settings)
    register_error_handlers(app)
    app.include_router(api_router)
    from app.integrations.supabase_project import mount
    from app.integrations.supabase_project import router as project_status

    mount(app)
    app.include_router(project_status, prefix="/api")
    return app


app = create_app()
