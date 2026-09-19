"""FastAPI entrypoint. `make dev` runs `uvicorn app.main:app`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.db.migrate import upgrade_to_head
from app.db.session import make_engine, make_session_factory
from app.models_ai.factory import build_providers


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.auto_migrate:
            upgrade_to_head(settings.sync_database_url)
        engine = make_engine(settings.database_url_resolved)
        app.state.engine = engine
        app.state.session_factory = make_session_factory(engine)
        if getattr(app.state, "providers", None) is None:
            app.state.providers = build_providers(settings)
        try:
            yield
        finally:
            repo = getattr(app.state, "repo", None)
            if repo is not None and hasattr(repo, "client"):
                await repo.client.close()
            await engine.dispose()

    app = FastAPI(title="AuDHS-Tutor", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.providers = None
    app.state.repo = None
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
