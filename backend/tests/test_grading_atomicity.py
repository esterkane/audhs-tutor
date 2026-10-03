"""Failure injection verifies the entire learning write set, from a new connection."""

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.events import EventWriter, Verb
from app.kernel import competency, memory
from app.kernel import session as ksession
from app.kernel.seed import load_seed
from app.models_ai import registry

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"
TABLES = (
    models.AssessmentAttempt,
    models.CompetencyEvidence,
    models.CompetencyState,
    models.ReviewItem,
    models.MemoryState,
    models.ReviewLog,
    models.LearningEvent,
    models.SessionCheckpoint,
)


async def snapshot(factory):
    async with factory() as db:
        return {
            table.__tablename__: [
                dict(row)
                for row in (await db.execute(select(table.__table__).order_by(table.id))).mappings()
            ]
            for table in TABLES
        }


@pytest.mark.parametrize(
    "stage",
    [
        "attempt",
        "attempted",
        "graded",
        "evidenced",
        "reviewed",
        "ensure",
        "checkpoint",
        "refresh",
        "commit",
    ],
)
@pytest.mark.parametrize("existing", [False, True])
async def test_learning_writes_rollback_together(
    client, db, session_factory, monkeypatch, stage, existing
):
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    started = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    item = (await client.get("/api/assess/next", params={"session_id": started["id"]})).json()[
        "item"
    ]
    if existing:
        first = await client.post(
            "/api/assess/attempt",
            json={
                "content_version": item["content_version"],
                "session_id": started["id"],
                "assessment_id": item["id"],
                "answer": "0",
            },
        )
        assert first.status_code == 200
    session = await db.get(models.Session, started["id"])
    await ksession.save_checkpoint(db, session, {"skill_id": item["skill_id"], "hint_level": 2})
    before = await snapshot(session_factory)
    if stage in {"attempted", "graded", "evidenced", "reviewed"}:
        original = EventWriter.emit

        async def fail(self, verb, *args, **kwargs):
            result = await original(self, verb, *args, **kwargs)
            if verb == Verb(stage):
                raise RuntimeError("injected failure")
            return result

        monkeypatch.setattr(EventWriter, "emit", fail)
    elif stage in {"attempt", "commit"}:
        original = AsyncSession.flush

        async def fail(self, *args, **kwargs):
            if stage == "attempt":
                await original(self, *args, **kwargs)
            raise RuntimeError("injected failure")

        monkeypatch.setattr(AsyncSession, "flush" if stage == "attempt" else "commit", fail)
    else:
        module, name = {
            "ensure": (memory, "ensure_item"),
            "checkpoint": (ksession, "save_checkpoint"),
            "refresh": (competency, "refresh"),
        }[stage]
        original = getattr(module, name)

        async def fail(*args, **kwargs):
            await original(*args, **kwargs)
            raise RuntimeError("injected failure")

        monkeypatch.setattr(module, name, fail)
    with pytest.raises(RuntimeError, match="injected failure"):
        await client.post(
            "/api/assess/attempt",
            json={
                "content_version": item["content_version"],
                "session_id": started["id"],
                "assessment_id": item["id"],
                "answer": "0",
            },
        )
    assert await snapshot(session_factory) == before
