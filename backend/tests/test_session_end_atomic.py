"""Session end and its recap event must not diverge on failure or concurrent completion."""

import asyncio

import pytest
from sqlalchemy import select

from app.db.events import EventWriter
from app.db.models import LearningEvent, Session
from app.kernel import session
from app.schemas.common import Mode


async def test_failed_recap_write_leaves_session_retryable(db, learner, monkeypatch):
    s = await session.start(db, learner.id, mode=Mode.STEADY, energy=3)
    sid = s.id
    original = EventWriter.emit

    async def fail(*args, **kwargs):
        await original(*args, **kwargs)
        raise RuntimeError("injected after event flush")

    with monkeypatch.context() as patch:
        patch.setattr(EventWriter, "emit", fail)
        with pytest.raises(RuntimeError, match="injected"):
            await session.end(db, sid, energy_after=4, self_report=2, notes="Keep these notes")
    await db.rollback()
    saved = await db.get(Session, sid)
    assert saved.ended_at is None
    assert saved.energy_after is None
    assert not (
        await db.scalars(
            select(LearningEvent).where(
                LearningEvent.session_id == sid, LearningEvent.verb == "ended"
            )
        )
    ).all()
    await session.end(db, sid, energy_after=4, self_report=2, notes="Keep these notes")
    await session.end(db, sid, energy_after=1, self_report=1, notes="Must not overwrite")
    events = (
        await db.scalars(
            select(LearningEvent).where(
                LearningEvent.session_id == sid, LearningEvent.verb == "ended"
            )
        )
    ).all()
    assert len(events) == 1
    assert events[0].result_json == {
        "energy_after": 4,
        "self_report": 2,
        "notes": "Keep these notes",
    }


async def test_concurrent_end_preserves_one_matching_recap(db, learner, session_factory):
    s = await session.start(db, learner.id, mode=Mode.STEADY, energy=3)
    sid = s.id

    async def finish(value):
        async with session_factory() as worker:
            # Include a stale ORM instance to ensure the losing worker refreshes server state.
            await worker.get(Session, sid)
            return await session.end(
                worker, sid, energy_after=value, self_report=value, notes=str(value)
            )

    first, second = await asyncio.gather(finish(2), finish(4))
    assert first.ended_at == second.ended_at
    assert first.energy_after == second.energy_after
    await db.refresh(s)
    events = (
        await db.scalars(
            select(LearningEvent).where(
                LearningEvent.session_id == sid, LearningEvent.verb == "ended"
            )
        )
    ).all()
    assert len(events) == 1
    assert events[0].result_json == {
        "energy_after": s.energy_after,
        "self_report": s.energy_after,
        "notes": str(s.energy_after),
    }


async def test_end_commit_failure_rolls_back_recap_and_session(db, learner, monkeypatch):
    s = await session.start(db, learner.id, mode=Mode.STEADY, energy=3)
    sid = s.id

    async def fail():
        raise RuntimeError("commit unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(db, "commit", fail)
        with pytest.raises(RuntimeError, match="commit unavailable"):
            await session.end(db, sid, energy_after=4, self_report=2, notes="Retain draft")
    saved = await db.get(Session, sid)
    assert saved.ended_at is None
    assert not (
        await db.scalars(
            select(LearningEvent).where(
                LearningEvent.session_id == sid, LearningEvent.verb == "ended"
            )
        )
    ).all()
