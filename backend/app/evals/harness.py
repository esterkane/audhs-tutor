"""Shared world builder for evals and benchmarks: an isolated SQLite DB (never the learner's dev.db),
the seeded curriculum + registry, real providers, and the production Qdrant corpus for retrieval."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import PROJECT_ROOT, Settings, get_settings
from app.db.migrate import upgrade_to_head
from app.db.session import make_engine, make_session_factory
from app.kernel.learner import get_or_create_owner
from app.kernel.seed import load_seed
from app.knowledge.reindex import build_repo
from app.knowledge.repository import RetrievalRepository
from app.models_ai import registry
from app.models_ai.factory import build_gateway, installed_models
from app.models_ai.gateway import ModelGateway


@dataclass
class World:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    learner_id: str
    repo: RetrievalRepository | None = None

    async def close(self) -> None:
        if self.repo is not None and hasattr(self.repo, "client"):
            await self.repo.client.close()
        await self.engine.dispose()

    def gateway(self, db: AsyncSession) -> ModelGateway:
        return build_gateway(db, self.settings)


async def open_world(
    db_name: str, *, seed: str = "attention", with_repo: bool = True, fresh: bool = False
) -> World:
    base = get_settings()
    db_path = PROJECT_ROOT / "data" / db_name
    if fresh and db_path.exists():
        db_path.unlink()
    settings = base.model_copy(
        update={"database_url": f"sqlite+aiosqlite:///{db_path}", "auto_migrate": False}
    )
    upgrade_to_head(settings.sync_database_url)
    engine = make_engine(settings.database_url_resolved)
    factory = make_session_factory(engine)
    async with factory() as db:
        await load_seed(db, PROJECT_ROOT / "seeds" / seed)
        await registry.seed_defaults(db, installed_ollama_tags=await installed_models(settings))
        learner = await get_or_create_owner(db, display_name="eval-learner")
        repo = await build_repo(db, settings) if with_repo else None
    return World(settings, engine, factory, learner.id, repo)


def results_dir() -> Path:
    p = PROJECT_ROOT / "evals" / "results"
    p.mkdir(parents=True, exist_ok=True)
    return p
