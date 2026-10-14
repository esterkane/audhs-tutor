"""A failed session finish must preserve the resumable running block."""

import sqlite3

import pytest

from app.kernel import session as ksession


async def test_failure_before_recap_keeps_running_checkpoint(client, monkeypatch):
    started = (await client.post("/api/sessions", json={})).json()
    sid = started["id"]
    response = await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    assert response.status_code == 200
    before = (await client.get(f"/api/sessions/{sid}")).json()

    async def fail(*args, **kwargs):
        raise RuntimeError("injected before recap")

    with monkeypatch.context() as patch:
        patch.setattr(ksession, "end", fail)
        with pytest.raises(RuntimeError, match="injected before recap"):
            await client.post(f"/api/sessions/{sid}/end", json={"notes": "Retain my work"})
    after = (await client.get(f"/api/sessions/{sid}")).json()
    assert after == before


async def _explained_session(client, db):
    from app.db import models
    from app.db.events import EventWriter, Verb
    from app.schemas.common import ObjectType
    from tests.test_exercises import _node

    node = await _node(db)
    sid = (await client.post("/api/sessions", json={})).json()["id"]
    assert (
        await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    ).status_code == 200
    session = await db.get(models.Session, sid)
    checkpoint = await ksession.load_checkpoint(db, sid)
    await ksession.save_checkpoint(db, session, {**checkpoint, "skill_id": node.id})
    await EventWriter(db, ksession.event_context(session)).emit(
        Verb.EXPLAINED,
        ObjectType.NODE,
        node.id,
        result={"sentences": 1, "cited_sources": []},
        context={"node_id": node.id},
    )
    db.add(
        models.SessionCheckpoint(
            learner_id=session.learner_id,
            session_id=sid,
            packet_json={"legacy": True},
            ts="2000-01-01T00:00:00+00:00",
            expires_at="2000-01-02T00:00:00+00:00",
        )
    )
    await db.commit()
    return sid, session.learner_id


@pytest.mark.parametrize("stage", ["recall", "block", "prune", "recap", "commit", "cancel"])
async def test_end_preparation_rolls_back_entire_write_set(
    client, db, db_path, session_factory, monkeypatch, stage
):
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.api import sessions
    from app.db.events import EventWriter, Verb
    from app.kernel import blocks
    from tests._rows import dump_tables

    sid, owner_id = await _explained_session(client, db)
    url = f"sqlite:///{db_path}"
    before = dump_tables(url)
    error = asyncio.CancelledError if stage == "cancel" else RuntimeError
    targets = {
        "recall": (sessions, "ensure_recall_item_for_explained_skill"),
        "block": (blocks, "end_running"),
        "prune": (ksession, "prune_checkpoints"),
        "cancel": (ksession, "prune_checkpoints"),
        "recap": (EventWriter, "emit"),
        "commit": (AsyncSession, "commit"),
    }
    owner, method = targets[stage]
    original = getattr(owner, method)

    async def fail(*args, **kwargs):
        if stage == "commit":
            raise error("injected end failure")
        result = await original(*args, **kwargs)
        if stage != "recap" or args[1] == Verb.ENDED:
            raise error("injected end failure")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(owner, method, fail)
        with pytest.raises(error, match="injected end failure"):
            if stage == "cancel":
                # ASGI middleware converts cancellation into a no-response error;
                # exercise handler cancellation directly with its own DB session.
                from app.db.models import LearnerProfile

                async with session_factory() as worker:
                    owner = await worker.get(LearnerProfile, owner_id)
                    await sessions._end_session(
                        sid, sessions.SessionEnd(notes="Finish once"), worker, owner
                    )
            else:
                await client.post(f"/api/sessions/{sid}/end", json={"notes": "Finish once"})
    assert dump_tables(url) == before
    assert (
        await client.post(f"/api/sessions/{sid}/end", json={"notes": "Finish once"})
    ).status_code == 200
    saved = dump_tables(url)
    assert len(saved["review_item"]) == len(before["review_item"]) + 1
    assert len(saved["memory_state"]) == len(before["memory_state"]) + 1
    assert len(saved["session_checkpoint"]) == 1
    with sqlite3.connect(db_path) as conn:
        events = [
            r[0]
            for r in conn.execute(
                "SELECT verb FROM learning_event WHERE session_id=? ORDER BY rowid", (sid,)
            )
        ]
    assert events.count("block_ended") == 1
    assert events.count("ended") == 1
    assert events.index("block_ended") < events.index("ended")
    assert (await client.post(f"/api/sessions/{sid}/end", json={})).status_code == 200
    assert dump_tables(url) == saved


async def test_independent_finish_workers_share_one_cleanup(client, db, session_factory, db_path):
    import asyncio

    from app.api.sessions import SessionEnd, _end_session
    from app.db.models import LearnerProfile
    from tests._rows import dump_tables

    sid, owner_id = await _explained_session(client, db)

    async def finish(value):
        async with session_factory() as worker:
            owner = await worker.get(LearnerProfile, owner_id)
            # Bypass the process-local request lock to exercise SQLite serialization.
            return await _end_session(
                sid, SessionEnd(notes=str(value), energy_after=value), worker, owner
            )

    first, second = await asyncio.gather(finish(2), finish(4))
    assert first.ended_at == second.ended_at
    assert first.energy_after == second.energy_after
    saved = dump_tables(f"sqlite:///{db_path}")
    assert len(saved["review_item"]) == len(saved["memory_state"]) == 1
    with sqlite3.connect(db_path) as conn:
        events = [
            r[0]
            for r in conn.execute(
                "SELECT verb FROM learning_event WHERE session_id=? ORDER BY rowid", (sid,)
            )
        ]
    assert events.count("block_ended") == 1
    assert events.count("ended") == 1
    assert events.index("block_ended") < events.index("ended")
