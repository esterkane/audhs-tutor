"""Plan adaptation lifecycle regressions, pending the documented transaction change."""

import pytest

from app.kernel import blocks
from tests._rows import dump_tables


async def proposal(client):
    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    result = await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})
    assert result.status_code == 200 and result.json()["changed"]
    return sid, result.json()["proposal_id"]


@pytest.mark.parametrize("action", ["accept", "undo"])
async def test_plan_adaptation_cannot_change_completed_session(client, db_path, action):
    sid, aid = await proposal(client)
    if action == "undo":
        accepted = await client.post(
            f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
        )
        assert accepted.status_code == 200
    await client.post(f"/api/sessions/{sid}/end", json={})
    before = dump_tables(f"sqlite:///{db_path}")
    if action == "accept":
        result = await client.post(
            f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
        )
    else:
        result = await client.post(f"/api/adaptations/{aid}/undo")
    assert result.status_code == 409
    assert dump_tables(f"sqlite:///{db_path}") == before


@pytest.mark.parametrize("action", ["accept", "undo"])
async def test_plan_version_failure_leaves_plan_and_decision_unchanged(
    client, db_path, monkeypatch, action
):
    sid, aid = await proposal(client)
    if action == "undo":
        await client.post(
            f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
        )
    before = dump_tables(f"sqlite:///{db_path}")

    async def fail(*args, **kwargs):
        raise RuntimeError("plan version failure")

    monkeypatch.setattr(blocks, "bump_plan_version", fail)
    with pytest.raises(RuntimeError, match="plan version failure"):
        if action == "accept":
            await client.post(
                f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
            )
        else:
            await client.post(f"/api/adaptations/{aid}/undo")
    assert dump_tables(f"sqlite:///{db_path}") == before


@pytest.mark.parametrize("action", ["accept", "undo"])
@pytest.mark.parametrize("failure", ["event", "cancel", "commit"])
async def test_adaptation_rollback(client, db_path, session_factory, monkeypatch, action, failure):
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.events import EventWriter

    sid, aid = await proposal(client)
    if action == "undo":
        await client.post(
            f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
        )
    before = dump_tables(f"sqlite:///{db_path}")
    original = EventWriter.emit
    error = asyncio.CancelledError if failure == "cancel" else RuntimeError

    async def fail_event(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise error("injected adaptation failure")

    async def fail_commit(*args, **kwargs):
        raise error("injected adaptation failure")

    if failure == "commit":
        monkeypatch.setattr(AsyncSession, "commit", fail_commit)
    else:
        monkeypatch.setattr(EventWriter, "emit", fail_event)
    from app.db.models import Session
    from app.kernel import adaptation

    async with session_factory() as db:
        session = await db.get(Session, sid)
        with pytest.raises(error, match="injected adaptation failure"):
            if action == "accept":
                await adaptation.decide(db, session.learner_id, aid, "try", session=session)
            else:
                await adaptation.undo(db, session.learner_id, aid)
    assert dump_tables(f"sqlite:///{db_path}") == before


@pytest.mark.parametrize("action", ["accept", "undo", "dismiss"])
async def test_independent_adaptation_workers_record_one_decision(
    client, session_factory, db_path, action
):
    import asyncio
    import sqlite3

    from app.db.models import Session
    from app.kernel import adaptation

    sid, aid = await proposal(client)
    if action == "undo":
        await client.post(
            f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
        )

    async def worker(decision):
        async with session_factory() as db:
            session = await db.get(Session, sid)
            try:
                if action == "undo":
                    await adaptation.undo(db, session.learner_id, aid)
                else:
                    await adaptation.decide(db, session.learner_id, aid, decision, session=session)
                return True
            except ValueError as exc:
                assert str(exc) in ("nothing to undo", "this proposal was already decided")
                return False

    results = await asyncio.gather(worker("try"), worker("no" if action == "dismiss" else "try"))
    assert sorted(results) == [False, True]
    with sqlite3.connect(db_path) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM adaptation_decision WHERE adaptation_id=?", (aid,)
            ).fetchone()[0]
            == 1
        )
        verb = "undone" if action == "undo" else "decided"
        assert (
            conn.execute(
                "SELECT count(*) FROM learning_event WHERE object_id=? AND verb=?", (aid, verb)
            ).fetchone()[0]
            == 1
        )


async def test_plan_cannot_be_accepted_for_different_session(client, db_path):
    sid, aid = await proposal(client)
    other = (await client.post("/api/sessions", json={})).json()["id"]
    before = dump_tables(f"sqlite:///{db_path}")
    response = await client.post(
        f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": other}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "plan_session_mismatch"
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_completed_plan_can_be_dismissed(client):
    sid, aid = await proposal(client)
    await client.post(f"/api/sessions/{sid}/end", json={})
    response = await client.post(f"/api/adaptations/{aid}/decide", json={"decision": "no"})
    assert response.status_code == 200


@pytest.mark.parametrize("action", ["accept", "undo"])
@pytest.mark.parametrize("finish_first", [False, True])
async def test_adaptation_and_finish_serialize(
    client, session_factory, monkeypatch, action, finish_first
):
    import asyncio

    from app.api.sessions import SessionEnd, _end_session
    from app.core.errors import AppError
    from app.db.models import LearnerProfile, Session
    from app.kernel import adaptation
    from app.kernel import session as ksession

    sid, aid = await proposal(client)
    if action == "undo":
        await client.post(
            f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
        )
    ready, waiting, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    original = ksession.lock_for_transition

    async def controlled(*args):
        if asyncio.current_task().get_name() == "first":
            result = await original(*args)
            ready.set()
            await release.wait()
            return result
        waiting.set()
        return await original(*args)

    monkeypatch.setattr(ksession, "lock_for_transition", controlled)

    async def worker(finish):
        async with session_factory() as db:
            s = await db.get(Session, sid)
            owner = await db.get(LearnerProfile, s.learner_id)
            if finish:
                return await _end_session(sid, SessionEnd(), db, owner)
            try:
                if action == "accept":
                    return await adaptation.decide(db, owner.id, aid, "try", session=s)
                return await adaptation.undo(db, owner.id, aid)
            except AppError as exc:
                assert finish_first and exc.code == "session_ended"
                return exc

    first = asyncio.create_task(worker(finish_first), name="first")
    await asyncio.wait_for(ready.wait(), 5)
    second = asyncio.create_task(worker(not finish_first), name="second")
    await asyncio.wait_for(waiting.wait(), 5)
    release.set()
    results = await asyncio.wait_for(asyncio.gather(first, second), 10)
    if finish_first:
        assert isinstance(results[1], AppError)
    saved = (await client.get(f"/api/sessions/{sid}")).json()
    assert saved["ended_at"] is not None
    assert saved["state"]["block_status"] == "ended"


@pytest.mark.parametrize("endpoint", ["observe", "decide"])
async def test_foreign_session_context_does_not_write(client, db, db_path, endpoint):
    from app.db.models import LearnerProfile, Session

    sid, aid = await proposal(client)
    other = LearnerProfile(display_name="Other learner")
    db.add(other)
    await db.flush()
    foreign = Session(learner_id=other.id, mode="steady", energy=3)
    db.add(foreign)
    await db.commit()
    before = dump_tables(f"sqlite:///{db_path}")

    async def request(session_id):
        if endpoint == "observe":
            return await client.post("/api/adaptations/observe", params={"session_id": session_id})
        return await client.post(
            f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": session_id}
        )

    response = await request(foreign.id)
    missing = await request("missing-session")
    assert response.status_code == missing.status_code == 404
    assert response.json() == missing.json()
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_sessionless_plan_is_not_applied(client, db, db_path):
    from app.db.models import Adaptation

    sid, aid = await proposal(client)
    a = await db.get(Adaptation, aid)
    a.session_id = None
    await db.commit()
    before = dump_tables(f"sqlite:///{db_path}")
    response = await client.post(
        f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
    )
    assert response.status_code == 400
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_completed_plan_history_does_not_offer_undo(client):
    sid, aid = await proposal(client)
    accepted = await client.post(
        f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
    )
    entry = next(e for e in accepted.json()["entries"] if e["id"] == aid)
    assert entry["in_effect"] is True
    await client.post(f"/api/sessions/{sid}/end", json={})
    saved = (await client.get("/api/adaptations/log")).json()
    entry = next(e for e in saved["entries"] if e["id"] == aid)
    assert entry["in_effect"] is False
    assert entry["decision"] == "try"
    assert entry["undone_at"] is None  # completion is not a fabricated undo
