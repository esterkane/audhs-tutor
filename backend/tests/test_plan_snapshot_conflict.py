"""An old plan snapshot must not replace an activity already under way."""

import pytest


@pytest.mark.parametrize("action", ["accept", "undo"])
async def test_old_plan_snapshot_cannot_rewrite_running_activity(client, action):
    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    proposal = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})).json()
    aid = proposal["proposal_id"]
    assert aid is not None
    if action == "undo":
        response = await client.post(
            f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
        )
        assert response.status_code == 200
    await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    before = (await client.get(f"/api/sessions/{sid}")).json()
    assert before["state"]["block_index"] == 1
    if action == "accept":
        response = await client.post(
            f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
        )
    else:
        response = await client.post(f"/api/adaptations/{aid}/undo")
    after = (await client.get(f"/api/sessions/{sid}")).json()
    assert after["plan"][:2] == before["plan"][:2], (
        action,
        response.status_code,
        before["plan"][:2],
        after["plan"][:2],
    )


@pytest.mark.parametrize("action", ["accept", "undo"])
async def test_refresh_is_separate_review_and_preserves_activity(client, action):
    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    aid = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})).json()[
        "proposal_id"
    ]
    if action == "undo":
        assert (
            await client.post(
                f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
            )
        ).status_code == 200
    await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    before = (await client.get(f"/api/sessions/{sid}")).json()
    preview = await client.post(f"/api/adaptations/{aid}/refresh-plan")
    assert preview.status_code == 200, preview.text
    new = preview.json()
    assert new["plan_state"] == "ready" and new["id"] != aid
    assert new["protected_blocks"] == 2
    assert new["plan_blocks"][:2] == before["plan"][:2]
    saved = (await client.get(f"/api/sessions/{sid}")).json()
    assert saved["plan"] == before["plan"] and saved["checkpoint"] == before["checkpoint"]
    repeated = await client.post(f"/api/adaptations/{aid}/refresh-plan")
    assert repeated.json()["id"] == new["id"]
    accepted = await client.post(
        f"/api/adaptations/{new['id']}/decide", json={"decision": "try", "session_id": sid}
    )
    assert accepted.status_code == 200, accepted.text
    after = (await client.get(f"/api/sessions/{sid}")).json()
    assert after["plan"] == new["plan_blocks"]
    assert after["plan"][:2] == before["plan"][:2]
    assert after["state"]["block_started_at"] == before["state"]["block_started_at"]
    assert (
        after["energy"] == before["energy"]
    )  # adjusting future durations is not a new energy self-report
    log = (await client.get("/api/adaptations/log")).json()["entries"]
    original = next(e for e in log if e["id"] == aid)
    assert original["decision"] == ("try" if action == "undo" else None)
    assert original["undone_at"] is None


@pytest.mark.parametrize("decision", ["try", "no", "never"])
async def test_superseded_proposal_cannot_be_decided(client, db_path, decision):
    from tests._rows import dump_tables

    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    aid = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})).json()[
        "proposal_id"
    ]
    preview = await client.post(f"/api/adaptations/{aid}/refresh-plan")
    assert preview.status_code == 200
    before = dump_tables(f"sqlite:///{db_path}")
    response = await client.post(
        f"/api/adaptations/{aid}/decide", json={"decision": decision, "session_id": sid}
    )
    assert response.status_code == 409
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_refresh_follows_latest_successor(client):
    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    a = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})).json()[
        "proposal_id"
    ]
    b = (await client.post(f"/api/adaptations/{a}/refresh-plan")).json()["id"]
    c = (await client.post(f"/api/adaptations/{b}/refresh-plan")).json()["id"]
    assert c != b
    assert (await client.post(f"/api/adaptations/{a}/refresh-plan")).json()["id"] == c


@pytest.mark.parametrize("decision", ["try", "no", "never", None])
async def test_replan_returns_its_exact_stored_preview_or_respects_decline(client, decision):
    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    a = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})).json()[
        "proposal_id"
    ]
    if decision:
        assert (
            await client.post(
                f"/api/adaptations/{a}/decide", json={"decision": decision, "session_id": sid}
            )
        ).status_code == 200
    response = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 4})).json()
    if decision in ("no", "never"):
        assert response["proposal_id"] is None and response["changed"] is False
    else:
        assert response["proposal_id"] != a
        pending = (await client.get("/api/adaptations")).json()["proposals"]
        matched = next(p for p in pending if p["id"] == response["proposal_id"])
        assert matched["plan_blocks"] == response["plan"]["blocks"]


async def test_stale_undo_preview_retains_earlier_energy_intent(client):
    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    aid = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})).json()[
        "proposal_id"
    ]
    await client.post(f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid})
    await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 0})
    first = (await client.post(f"/api/adaptations/{aid}/refresh-plan")).json()
    assert first["value"]["energy"] == 5
    await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": 1})
    response = await client.post(f"/api/adaptations/{first['id']}/refresh-plan")
    assert response.status_code == 200, response.text
    second = response.json()
    assert second["value"]["energy"] == 5
    assert second["evidence"]["refresh_kind"] == "undo_adjustment"
    assert "current energy setting stays unchanged" in second["why"]
    assert (await client.get(f"/api/sessions/{sid}")).json()["energy"] == 1


async def test_refresh_failure_rolls_back_preview_and_supersession(client, db_path, monkeypatch):
    from app.kernel.adaptation import EventWriter
    from tests._rows import dump_tables

    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    aid = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})).json()[
        "proposal_id"
    ]
    before = dump_tables(f"sqlite:///{db_path}")

    async def fail(*args, **kwargs):
        raise RuntimeError("preview event failure")

    monkeypatch.setattr(EventWriter, "emit", fail)
    with pytest.raises(RuntimeError, match="preview event failure"):
        await client.post(f"/api/adaptations/{aid}/refresh-plan")
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_refresh_after_finish_is_rejected_without_writes(client, db_path):
    from tests._rows import dump_tables

    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    aid = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})).json()[
        "proposal_id"
    ]
    await client.post(f"/api/sessions/{sid}/end", json={})
    before = dump_tables(f"sqlite:///{db_path}")
    assert (await client.post(f"/api/adaptations/{aid}/refresh-plan")).status_code == 409
    assert dump_tables(f"sqlite:///{db_path}") == before


async def test_legacy_unbound_proposal_requires_review(client, session_factory, db_path):
    from app.db.models import Adaptation
    from tests._rows import dump_tables

    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    aid = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})).json()[
        "proposal_id"
    ]
    async with session_factory() as db:
        row = await db.get(Adaptation, aid)
        row.evidence_json = {k: v for k, v in row.evidence_json.items() if k != "plan_binding"}
        await db.commit()
    before = dump_tables(f"sqlite:///{db_path}")
    response = await client.post(
        f"/api/adaptations/{aid}/decide", json={"decision": "try", "session_id": sid}
    )
    assert response.status_code == 409
    assert dump_tables(f"sqlite:///{db_path}") == before
    refreshed = await client.post(f"/api/adaptations/{aid}/refresh-plan")
    assert refreshed.status_code == 200
    preview = refreshed.json()
    assert preview["plan_state"] == "ready"
    accepted = await client.post(
        f"/api/adaptations/{preview['id']}/decide", json={"decision": "try", "session_id": sid}
    )
    assert accepted.status_code == 200


async def test_concurrent_refresh_creates_one_preview(client, session_factory, db_path):
    import asyncio
    import sqlite3

    from app.db.models import Session
    from app.kernel import adaptation

    sid = (await client.post("/api/sessions", json={"energy": 5})).json()["id"]
    aid = (await client.post("/api/plan/replan", json={"session_id": sid, "energy": 1})).json()[
        "proposal_id"
    ]

    async def worker():
        async with session_factory() as db:
            session = await db.get(Session, sid)
            return (await adaptation.refresh_plan(db, session.learner_id, aid)).id

    ids = await asyncio.wait_for(asyncio.gather(worker(), worker()), 10)
    assert ids[0] == ids[1] and ids[0] != aid
    with sqlite3.connect(db_path) as conn:
        assert (
            conn.execute("SELECT count(*) FROM adaptation WHERE session_id=?", (sid,)).fetchone()[0]
            == 2
        )
        assert conn.execute("SELECT count(*) FROM adaptation_decision").fetchone()[0] == 0
