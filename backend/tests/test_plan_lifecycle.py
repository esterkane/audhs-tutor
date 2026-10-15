"""Standalone plan writes must serialize with Finish and retain transaction ownership."""

from types import SimpleNamespace

import pytest
from starlette.requests import Request

from app.api import plan
from app.core.errors import AppError
from app.db.models import LearnerProfile, Session
from tests._rows import dump_tables


async def invoke(action, sid, db, owner):
    request = Request({"type": "http", "app": SimpleNamespace(state=SimpleNamespace())})
    if action == "start":
        return await plan.start_block(plan.BlockEvent(session_id=sid, index=0), request, db, owner)
    if action == "end":
        return await plan.end_block(plan.BlockEvent(session_id=sid, index=0), request, db, owner)
    if action == "extend":
        return await plan.extend_block(plan.BlockExtend(session_id=sid, index=0), db, owner)
    return await plan.replan(plan.ReplanIn(session_id=sid, energy=1), db, owner)


@pytest.mark.parametrize("action", ["start", "end", "extend", "replan"])
async def test_stale_plan_worker_cannot_write_after_finish(client, db, db_path, action):
    sid = (await client.post("/api/sessions", json={})).json()["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    stale = await db.get(Session, sid)
    owner = await db.get(LearnerProfile, stale.learner_id)
    assert stale.ended_at is None
    assert (await client.post(f"/api/sessions/{sid}/end", json={})).status_code == 200
    before = dump_tables(f"sqlite:///{db_path}")
    with pytest.raises(AppError, match="session has ended"):
        await invoke(action, sid, db, owner)
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_replan_failure_does_not_save_energy_without_proposal(client, db_path, monkeypatch):
    from app.kernel import adaptation

    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    before = dump_tables(f"sqlite:///{db_path}")

    async def fail(*args, **kwargs):
        raise RuntimeError("injected proposal failure")

    monkeypatch.setattr(adaptation, "propose", fail)
    with pytest.raises(RuntimeError, match="injected proposal failure"):
        await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})
    assert dump_tables(f"sqlite:///{db_path}") == before


@pytest.mark.parametrize("action", ["start", "end", "extend", "replan"])
@pytest.mark.parametrize("finish_first", [False, True])
async def test_plan_write_and_finish_are_serialized(
    client, session_factory, db_path, monkeypatch, action, finish_first
):
    import asyncio
    import sqlite3

    from app.api.sessions import SessionEnd, _end_session
    from app.kernel import session as ksession

    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    if action != "start":
        await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    locked = asyncio.Event()
    competing = asyncio.Event()
    release = asyncio.Event()
    original = ksession.lock_for_transition

    async def controlled_lock(*args):
        if asyncio.current_task().get_name() == "first-writer":
            result = await original(*args)
            locked.set()
            await release.wait()
            return result
        competing.set()
        return await original(*args)

    monkeypatch.setattr(ksession, "lock_for_transition", controlled_lock)

    async def worker(finish):
        async with session_factory() as db:
            s = await db.get(Session, sid)
            owner = await db.get(LearnerProfile, s.learner_id)
            if finish:
                return await _end_session(sid, SessionEnd(), db, owner)
            try:
                return await invoke(action, sid, db, owner)
            except AppError as error:
                assert finish_first and error.code == "session_ended"
                return error

    first = asyncio.create_task(worker(finish_first), name="first-writer")
    await asyncio.wait_for(locked.wait(), timeout=5)
    second = asyncio.create_task(worker(not finish_first), name="second-writer")
    await asyncio.wait_for(competing.wait(), timeout=5)
    release.set()
    results = await asyncio.wait_for(asyncio.gather(first, second), timeout=10)
    if finish_first:
        assert isinstance(results[1], AppError)
    current = (await client.get(f"/api/sessions/{sid}")).json()
    assert current["ended_at"] is not None
    assert current["state"]["block_status"] in (None, "ended")
    with sqlite3.connect(db_path) as conn:
        verbs = [
            r[0]
            for r in conn.execute(
                "SELECT verb FROM learning_event WHERE session_id=? ORDER BY rowid", (sid,)
            )
        ]
    assert verbs.count("ended") == 1
    assert verbs[-1] == "ended"


@pytest.mark.parametrize("action", ["start", "end", "extend", "replan"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_staged_plan_write_rolls_back_on_error_or_cancellation(
    client, session_factory, db_path, monkeypatch, action, cancel
):
    import asyncio

    from app.kernel import adaptation, blocks

    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    if action != "start":
        await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    before = dump_tables(f"sqlite:///{db_path}")
    target = adaptation if action == "replan" else blocks
    name = "propose" if action == "replan" else action
    original = getattr(target, name)
    error = asyncio.CancelledError if cancel else RuntimeError

    async def interrupted(*args, **kwargs):
        await original(*args, **kwargs)
        raise error("after staged plan write")

    monkeypatch.setattr(target, name, interrupted)
    async with session_factory() as db:
        s = await db.get(Session, sid)
        owner = await db.get(LearnerProfile, s.learner_id)
        with pytest.raises(error, match="after staged plan write"):
            await invoke(action, sid, db, owner)
    assert dump_tables(f"sqlite:///{db_path}") == before


@pytest.mark.parametrize("action", ["start", "end", "extend"])
async def test_independent_duplicate_plan_workers(client, session_factory, db_path, action):
    import asyncio
    import sqlite3

    sid = (await client.post("/api/sessions", json={})).json()["id"]
    if action != "start":
        await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})

    async def worker():
        async with session_factory() as db:
            s = await db.get(Session, sid)
            owner = await db.get(LearnerProfile, s.learner_id)
            return await invoke(action, sid, db, owner)

    await asyncio.gather(worker(), worker())
    state = (await client.get(f"/api/sessions/{sid}")).json()["state"]
    if action == "extend":
        assert state["timer_extension_min"] == 10
    else:
        assert state["block_status"] == ("running" if action == "start" else "ended")
        with sqlite3.connect(db_path) as conn:
            count = conn.execute(
                "SELECT count(*) FROM learning_event WHERE session_id=? AND verb=?",
                (sid, "block_started" if action == "start" else "block_ended"),
            ).fetchone()[0]
        assert count == 1


@pytest.mark.parametrize("action", ["start", "end", "extend", "replan"])
async def test_final_commit_failure_rolls_back(client, db_path, monkeypatch, action):
    from sqlalchemy.ext.asyncio import AsyncSession

    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    if action != "start":
        await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    before = dump_tables(f"sqlite:///{db_path}")

    async def fail(*args, **kwargs):
        raise RuntimeError("commit failed")

    monkeypatch.setattr(AsyncSession, "commit", fail)
    path = "/api/plan/replan" if action == "replan" else f"/api/plan/blocks/{action}"
    payload = (
        {"session_id": sid, "energy": 1} if action == "replan" else {"session_id": sid, "index": 0}
    )
    with pytest.raises(RuntimeError, match="commit failed"):
        await client.post(path, json=payload)
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_lost_extension_commit_ack_requires_state_read(client, db_path, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    sid = (await client.post("/api/sessions", json={})).json()["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    original = AsyncSession.commit

    async def lose_ack(self):
        await original(self)
        raise RuntimeError("ack lost")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", lose_ack)
        with pytest.raises(RuntimeError, match="ack lost"):
            await client.post("/api/plan/blocks/extend", json={"session_id": sid, "index": 0})
    saved = dump_tables(f"sqlite:///{db_path}")
    state = (await client.get(f"/api/sessions/{sid}")).json()["state"]
    assert state["timer_extension_min"] == 5
    assert dump_tables(f"sqlite:///{db_path}") == saved
    # A second explicit extension is additive, not an idempotent replay.
    response = await client.post("/api/plan/blocks/extend", json={"session_id": sid, "index": 0})
    assert response.json()["timer_extension_min"] == 10


async def test_unchanged_replan_still_saves_explicit_energy(client, db):
    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    response = await client.post(
        "/api/plan/replan", json={"session_id": sid, "energy": 1, "from_index": 400}
    )
    assert response.status_code == 200
    assert response.json()["changed"] is False
    assert response.json()["proposal_id"] is None
    s = await db.get(Session, sid, populate_existing=True)
    assert s.energy == 1
