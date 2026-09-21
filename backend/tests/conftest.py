"""Shared fixtures: fresh SQLite per test (create_all + guard triggers), learner, app client."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db import models
from app.db.base import Base
from app.db.session import make_engine, make_session_factory
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.main import create_app
from app.models_ai.fake import FakeProvider
from app.models_ai.provider import ModelSpec


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def settings(db_path: Path, tmp_path_factory: pytest.TempPathFactory) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{db_path}",
        auto_migrate=False,
        anthropic_api_key="",
        daily_budget_usd=1.0,
        ingest_roots=f"{Path(__file__).resolve().parents[2]},{tmp_path_factory.getbasetemp()}",
        voice_dir=str(
            tmp_path_factory.getbasetemp() / "voice"
        ),  # retained recordings never leave tmp
        _env_file=None,  # type: ignore[call-arg]
    )


@pytest.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    eng = make_engine(settings.database_url_resolved)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return make_session_factory(engine)


@pytest.fixture
async def db(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        yield s


@pytest.fixture
async def learner(db: AsyncSession) -> models.LearnerProfile:
    lp = models.LearnerProfile(display_name="Test Learner")
    db.add(lp)
    await db.commit()
    return lp


@pytest.fixture
def fake_local() -> FakeProvider:
    return FakeProvider(
        text="(analogy) Keys are labels, values are contents. Next: try the two-token example."
    )


@pytest.fixture
def fake_repo() -> SqliteHybridRepository:
    return SqliteHybridRepository(
        FakeProvider(vectors_dim=32),
        ModelSpec(registry_id="fake-embed", provider="fake", model="f"),
        dims=32,
    )


@pytest.fixture
async def client(
    settings: Settings,
    engine: AsyncEngine,
    fake_local: FakeProvider,
    fake_repo: SqliteHybridRepository,
) -> AsyncIterator[AsyncClient]:
    """App client with fake providers and an in-memory retrieval repo (no Ollama/Qdrant needed)."""
    app = create_app(settings)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.providers = {"ollama": fake_local, "anthropic": FakeProvider(text="hosted")}
    app.state.repo = fake_repo
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
