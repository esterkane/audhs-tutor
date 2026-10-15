"""Checkpoint reads/writes are owned and cannot revive a completed session."""

import pytest

from app.db.models import LearnerProfile, Session
from tests._rows import dump_tables


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_foreign_session_read_or_checkpoint_matches_missing(client, db, db_path, method):
    own_id = (await client.post("/api/sessions", json={})).json()["id"]
    own = await db.get(Session, own_id)
    other = LearnerProfile(display_name="Other learner")
    db.add(other)
    await db.flush()
    foreign = Session(
        learner_id=other.id, mode="steady", energy=3, planned_blocks_json=own.planned_blocks_json
    )
    db.add(foreign)
    await db.commit()
    before = dump_tables(f"sqlite:///{db_path}")

    async def request(sid):
        if method == "GET":
            return await client.get(f"/api/sessions/{sid}")
        return await client.post(f"/api/sessions/{sid}/checkpoint", json={"phase": "teach"})

    response = await request(foreign.id)
    missing = await request("missing-session")
    assert response.status_code == missing.status_code == 404
    assert response.json() == missing.json()
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_checkpoint_after_finish_rejected_without_writes(client, db_path):
    sid = (await client.post("/api/sessions", json={})).json()["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    await client.post(f"/api/sessions/{sid}/end", json={})
    before = dump_tables(f"sqlite:///{db_path}")
    response = await client.post(f"/api/sessions/{sid}/checkpoint", json={"phase": "teach"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "session_ended"
    assert dump_tables(f"sqlite:///{db_path}") == before


async def call_checkpoint(db, sid, body):
    from types import SimpleNamespace

    from starlette.requests import Request

    from app.api import sessions

    s = await db.get(Session, sid)
    owner = await db.get(LearnerProfile, s.learner_id)
    request = Request({"type": "http", "app": SimpleNamespace(state=SimpleNamespace())})
    return await sessions.checkpoint(sid, sessions.CheckpointIn(**body), request, db, owner)


@pytest.mark.parametrize("other", ["finish", "advance"])
@pytest.mark.parametrize("checkpoint_first", [False, True])
async def test_checkpoint_serializes_with_lifecycle(
    client, session_factory, db_path, monkeypatch, other, checkpoint_first
):
    import asyncio

    from app.api.sessions import SessionEnd, _end_session
    from app.core.errors import AppError
    from app.kernel import blocks
    from app.kernel import session as ksession

    sid = (await client.post("/api/sessions", json={})).json()["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    locked, waiting, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    original = ksession.lock_for_transition

    async def controlled(*args):
        if asyncio.current_task().get_name() == "first":
            result = await original(*args)
            locked.set()
            await release.wait()
            return result
        waiting.set()
        return await original(*args)

    monkeypatch.setattr(ksession, "lock_for_transition", controlled)

    async def worker(checkpoint):
        async with session_factory() as db:
            s = await db.get(Session, sid)
            owner = await db.get(LearnerProfile, s.learner_id)
            if checkpoint:
                try:
                    return await call_checkpoint(
                        db, sid, {"block_index": 0, "extra": {"marker": "kept"}}
                    )
                except AppError as exc:
                    assert not checkpoint_first
                    assert exc.code == ("session_ended" if other == "finish" else "stale_block")
                    return exc
            if other == "finish":
                return await _end_session(sid, SessionEnd(), db, owner)
            return await blocks.advance(db, s, from_index=0)

    first = asyncio.create_task(worker(checkpoint_first), name="first")
    await asyncio.wait_for(locked.wait(), 5)
    second = asyncio.create_task(worker(not checkpoint_first), name="second")
    await asyncio.wait_for(waiting.wait(), 5)
    release.set()
    await asyncio.wait_for(asyncio.gather(first, second), 10)
    saved = (await client.get(f"/api/sessions/{sid}")).json()
    assert saved["checkpoint"].get("marker") == ("kept" if checkpoint_first else None)
    if other == "finish":
        assert saved["ended_at"] is not None
        assert saved["state"]["block_status"] == "ended"
    else:
        assert saved["state"]["block_index"] == 1
        assert saved["state"]["block_status"] == "running"


@pytest.mark.parametrize("failure", ["after_save", "cancel", "commit"])
async def test_failed_checkpoint_keeps_prior_state(
    client, session_factory, db_path, monkeypatch, failure
):
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.kernel import session as ksession

    sid = (await client.post("/api/sessions", json={})).json()["id"]
    before = dump_tables(f"sqlite:///{db_path}")
    original = ksession.save_checkpoint
    error = asyncio.CancelledError if failure == "cancel" else RuntimeError

    async def fail_save(*args, **kwargs):
        await original(*args, **kwargs)
        raise error("injected checkpoint failure")

    async def fail_commit(*args):
        raise error("injected checkpoint failure")

    if failure == "commit":
        monkeypatch.setattr(AsyncSession, "commit", fail_commit)
    else:
        monkeypatch.setattr(ksession, "save_checkpoint", fail_save)
    async with session_factory() as db:
        with pytest.raises(error, match="injected checkpoint failure"):
            await call_checkpoint(db, sid, {"extra": {"marker": "not saved"}})
    assert dump_tables(f"sqlite:///{db_path}") == before
