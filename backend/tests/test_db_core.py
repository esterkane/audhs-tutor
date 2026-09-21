import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db import models
from app.db.base import Base
from app.db.migrate import upgrade_to_head

EXPECTED_TABLES = {
    "learner_profile",
    "learner_preference",
    "session",
    "session_checkpoint",
    "curriculum_draft",  # P4: reviewable course→curriculum drafts
    "content_report",  # P4: "this source/explanation is wrong" reports
    "budget_reservation",  # P6: hosted-call reservations against the daily cap
    "skill_node",
    "skill_edge",
    "learning_object",
    "representation",
    "competency_evidence",
    "competency_state",
    "review_item",
    "memory_state",
    "review_log",
    "assessment",
    "assessment_rubric",
    "assessment_attempt",
    "document",
    "document_version",
    "chunk",
    "chunk_provenance",
    "index_state",
    "model_registry",
    "parking_lot_item",
    "adaptation",
    "adaptation_decision",
    "experiment",
    "experiment_arm",
    "experiment_assignment",
    "experiment_observation",
    "tutor_trace",
    "retrieval_trace",
    "model_call",
    "learning_event",
    "ingest_run",  # course-material stage 1: progress + resume of an ingest run
    "ingest_run_item",
}


def test_all_phase1_tables_declared() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_learner_scoped_table_has_learner_id() -> None:
    # P4 tables ride along in export/wipe
    assert {"curriculum_draft", "content_report"} <= set(models.learner_scoped_tables())
    shared = {
        "learner_profile",
        "skill_node",
        "skill_edge",
        "learning_object",
        "representation",
        "assessment",
        "assessment_rubric",
        "document",
        "document_version",
        "chunk",
        "chunk_provenance",
        "index_state",
        "model_registry",
        "experiment_arm",
        "ingest_run",  # corpus tooling, not learner state
        "ingest_run_item",
    }
    for name, table in Base.metadata.tables.items():
        if name not in shared:
            assert "learner_id" in table.c, f"{name} lacks learner_id"


async def test_wal_and_foreign_keys(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        assert (await conn.execute(text("PRAGMA journal_mode"))).scalar() == "wal"
        assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar() == 1


async def _event(db: AsyncSession, learner: models.LearnerProfile) -> models.LearningEvent:
    ev = models.LearningEvent(
        learner_id=learner.id,
        actor="learner",
        verb="started",
        object_type="session",
        object_id="s1",
        domain="meta",
        activity_type="chat",
        mode="steady",
        energy=3,
    )
    db.add(ev)
    await db.commit()
    return ev


async def test_learning_event_is_append_only(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    ev_id = (await _event(db, learner)).id
    with pytest.raises(DBAPIError, match="append-only"):
        await db.execute(text("UPDATE learning_event SET verb='ended' WHERE id=:id"), {"id": ev_id})
    await db.rollback()
    with pytest.raises(DBAPIError, match="append-only"):
        await db.execute(text("DELETE FROM learning_event WHERE id=:id"), {"id": ev_id})
    await db.rollback()
    n = (await db.execute(text("SELECT count(*) FROM learning_event"))).scalar()
    assert n == 1


def test_alembic_head_matches_metadata(tmp_path: Path) -> None:
    """Committed migrations must build exactly the tables the ORM declares (+ guard triggers)."""
    url = f"sqlite:///{tmp_path / 'mig.db'}"
    upgrade_to_head(url)
    conn = sqlite3.connect(tmp_path / "mig.db")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert EXPECTED_TABLES <= tables
    triggers = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert {"learning_event_no_update", "learning_event_no_delete"} <= triggers
    from sqlalchemy import create_engine

    insp = inspect(create_engine(url))
    for name, table in Base.metadata.tables.items():
        migrated = {c["name"] for c in insp.get_columns(name)}
        assert migrated == {c.name for c in table.c}, f"column drift in {name}"
