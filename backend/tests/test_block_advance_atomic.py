"""Advancing activities must not partially end the current activity."""

import pytest

from app.kernel import blocks
from tests._rows import dump_tables


async def test_failed_next_start_preserves_running_activity(client, db_path, monkeypatch):
    sid = (await client.post("/api/sessions", json={})).json()["id"]
    assert (
        await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    ).status_code == 200
    before = dump_tables(f"sqlite:///{db_path}")

    async def fail(*args, **kwargs):
        raise RuntimeError("injected next start failure")

    with monkeypatch.context() as patch:
        patch.setattr(blocks, "start", fail)
        with pytest.raises(RuntimeError, match="injected next start failure"):
            await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_failure_after_next_start_rolls_back_and_retry_advances_once(
    client, db_path, monkeypatch
):
    sid = (await client.post("/api/sessions", json={})).json()["id"]
    assert (
        await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    ).status_code == 200
    before = dump_tables(f"sqlite:///{db_path}")
    original = blocks.start

    async def fail(*args, **kwargs):
        await original(*args, **kwargs)
        raise RuntimeError("injected after next checkpoint")

    with monkeypatch.context() as patch:
        patch.setattr(blocks, "start", fail)
        with pytest.raises(RuntimeError, match="injected after next checkpoint"):
            await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    assert dump_tables(f"sqlite:///{db_path}") == before
    response = await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    assert response.status_code == 200
    assert response.json()["block_index"] == 1
    saved = dump_tables(f"sqlite:///{db_path}")
    assert (
        await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    ).status_code == 200
    assert dump_tables(f"sqlite:///{db_path}") == saved


async def test_stale_worker_cannot_advance_ended_session(client, db, db_path):
    from app.core.errors import AppError
    from app.db.models import Session

    sid = (await client.post("/api/sessions", json={})).json()["id"]
    assert (
        await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    ).status_code == 200
    stale = await db.get(Session, sid)
    assert stale.ended_at is None
    assert (await client.post(f"/api/sessions/{sid}/end", json={})).status_code == 200
    before = dump_tables(f"sqlite:///{db_path}")
    with pytest.raises(AppError, match="session has ended"):
        await blocks.advance(db, stale, from_index=0)
    assert dump_tables(f"sqlite:///{db_path}") == before
    response = await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "session_ended"
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_independent_next_workers_do_not_duplicate_transition(
    client, session_factory, db_path
):
    import asyncio
    import sqlite3

    from app.db.models import Session

    sid = (await client.post("/api/sessions", json={})).json()["id"]
    assert (
        await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    ).status_code == 200

    async def advance():
        async with session_factory() as worker:
            s = await worker.get(Session, sid)
            return await blocks.advance(worker, s, from_index=0)

    first, second = await asyncio.gather(advance(), advance())
    assert first.block_index == second.block_index == 1
    with sqlite3.connect(db_path) as conn:
        events = [
            r[0]
            for r in conn.execute(
                "SELECT verb FROM learning_event WHERE session_id=? ORDER BY rowid", (sid,)
            )
        ]
    assert events.count("block_started") == 2
    assert events.count("block_ended") == 1
    assert [v for v in events if v.startswith("block_")] == [
        "block_started",
        "block_ended",
        "block_started",
    ]


async def test_advance_competes_with_finish_without_reopening(client, session_factory, db_path):
    import asyncio
    import sqlite3

    from app.api.sessions import SessionEnd, _end_session
    from app.core.errors import AppError
    from app.db.models import LearnerProfile, Session

    sid = (await client.post("/api/sessions", json={})).json()["id"]
    assert (
        await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    ).status_code == 200

    async def advance():
        async with session_factory() as worker:
            s = await worker.get(Session, sid)
            try:
                return await blocks.advance(worker, s, from_index=0)
            except AppError as exc:
                assert exc.code == "session_ended"
                return None

    async def finish():
        async with session_factory() as worker:
            s = await worker.get(Session, sid)
            owner = await worker.get(LearnerProfile, s.learner_id)
            return await _end_session(sid, SessionEnd(), worker, owner)

    _, finished = await asyncio.gather(advance(), finish())
    assert finished.ended_at is not None
    current = (await client.get(f"/api/sessions/{sid}")).json()
    assert current["state"]["block_status"] == "ended"
    with sqlite3.connect(db_path) as conn:
        events = [
            r[0]
            for r in conn.execute(
                "SELECT verb FROM learning_event WHERE session_id=? ORDER BY rowid", (sid,)
            )
        ]
    assert events.count("ended") == 1
    assert events[-1] == "ended"


async def test_advance_commit_failure_restores_original_state(client, db_path, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    sid = (await client.post("/api/sessions", json={})).json()["id"]
    response = await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    assert response.status_code == 200
    before = dump_tables(f"sqlite:///{db_path}")

    async def fail(*args, **kwargs):
        raise RuntimeError("injected advance commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", fail)
        with pytest.raises(RuntimeError, match="injected advance commit failure"):
            await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_cancellation_after_next_checkpoint_rolls_back(
    client, db_path, session_factory, monkeypatch
):
    import asyncio

    from app.db.models import Session

    sid = (await client.post("/api/sessions", json={})).json()["id"]
    response = await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    assert response.status_code == 200
    before = dump_tables(f"sqlite:///{db_path}")
    original = blocks.start

    async def cancel(*args, **kwargs):
        await original(*args, **kwargs)
        raise asyncio.CancelledError("injected after next checkpoint")

    with monkeypatch.context() as patch:
        patch.setattr(blocks, "start", cancel)
        async with session_factory() as worker:
            s = await worker.get(Session, sid)
            with pytest.raises(asyncio.CancelledError):
                await blocks.advance(worker, s, from_index=0)
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_lost_commit_ack_replays_same_next_without_duplicate_events(
    client, db_path, monkeypatch
):
    from sqlalchemy.ext.asyncio import AsyncSession

    sid = (await client.post("/api/sessions", json={})).json()["id"]
    response = await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    assert response.status_code == 200
    original = AsyncSession.commit

    async def lose_ack(self):
        await original(self)
        raise RuntimeError("injected after durable commit")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", lose_ack)
        with pytest.raises(RuntimeError, match="injected after durable commit"):
            await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    saved = dump_tables(f"sqlite:///{db_path}")
    response = await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    assert response.status_code == 200
    assert response.json()["block_index"] == 1
    assert dump_tables(f"sqlite:///{db_path}") == saved
