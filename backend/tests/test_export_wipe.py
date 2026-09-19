import sqlite3
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.portability import export_learner, wipe_learner
from app.db.session import sync_connect


async def _seed(db: AsyncSession, name: str) -> models.LearnerProfile:
    lp = models.LearnerProfile(display_name=name)
    db.add(lp)
    await db.flush()
    sess = models.Session(learner_id=lp.id, mode="steady", energy=3)
    db.add(sess)
    await db.flush()
    db.add(
        models.LearnerPreference(
            learner_id=lp.id, key="routing.chat", value_json="x", origin="explicit"
        )
    )
    db.add(
        models.LearningEvent(
            learner_id=lp.id,
            session_id=sess.id,
            actor="learner",
            verb="started",
            object_type="session",
            object_id=sess.id,
            domain="meta",
            activity_type="chat",
            mode="steady",
            energy=3,
        )
    )
    await db.commit()
    return lp


async def test_export_then_wipe_keeps_other_learners(db: AsyncSession, db_path: Path) -> None:
    a = await _seed(db, "A")
    b = await _seed(db, "B")
    conn = sync_connect(f"sqlite:///{db_path}")

    exported = export_learner(conn, a.id)
    assert len(exported["learner_profile"]) == 1
    assert len(exported["session"]) == 1
    assert len(exported["learner_preference"]) == 1
    assert len(exported["learning_event"]) == 1
    assert exported["learning_event"][0]["verb"] == "started"

    deleted = wipe_learner(conn, a.id)
    assert deleted["learning_event"] == 1 and deleted["learner_profile"] == 1

    conn.row_factory = None
    assert conn.execute("SELECT count(*) FROM learning_event").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM learner_profile").fetchone()[0] == 1
    assert export_learner(conn, b.id)["learning_event"][0]["learner_id"] == b.id
    # guards are back
    import pytest

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM learning_event")
