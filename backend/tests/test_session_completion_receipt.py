"""Owned, exact recap receipts; no synthetic historical backfill."""

from app.db import models
from app.db.base import utcnow_iso


async def test_exact_recap_retry_and_different_draft_conflict(client):
    started = await client.post("/api/sessions", json={"mode": "steady", "energy": 3})
    assert started.status_code == 201
    sid = started.json()["id"]
    path = f"/api/sessions/{sid}"
    assert (await client.get(path + "/completion")).json()["status"] == "open"
    body = {"confirm_recap": True, "notes": "Original notes", "energy_after": 4, "self_report": 2}
    assert (await client.post(path + "/end", json=body)).status_code == 200
    assert (await client.post(path + "/end", json=body)).status_code == 200
    conflict = await client.post(path + "/end", json={**body, "notes": "New local draft"})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "recap_not_confirmed"
    saved = (await client.get(path + "/completion")).json()
    assert saved["status"] == "saved"
    assert saved["recap"] == {"notes": "Original notes", "energy_after": 4, "self_report": 2}
    # Plain End still exits without changing a previously saved recap.
    assert (await client.post(path + "/end", json={})).status_code == 200
    assert (await client.get(path + "/completion")).json() == saved


async def test_empty_recap_and_missing_legacy_receipt(client, db):
    first = (await client.post("/api/sessions", json={})).json()["id"]
    path = f"/api/sessions/{first}"
    assert (
        await client.post(path + "/end", json={"confirm_recap": True, "notes": ""})
    ).status_code == 200
    assert (await client.post(path + "/end", json={"confirm_recap": True})).status_code == 200
    assert (await client.get(path + "/completion")).json()["recap"]["notes"] is None
    second = (await client.post("/api/sessions", json={})).json()["id"]
    legacy = await db.get(models.Session, second)
    legacy.ended_at = utcnow_iso()
    await db.commit()
    path = f"/api/sessions/{second}"
    assert (await client.get(path + "/completion")).json()["status"] == "unverified"
    assert (
        await client.post(path + "/end", json={"confirm_recap": True, "notes": "Cannot invent"})
    ).status_code == 409
    assert (await client.get(path + "/completion")).json()["recap"] is None


async def test_foreign_session_receipt_and_end_are_not_accessible(client, db):
    await client.get("/api/learner/me")
    foreign = models.LearnerProfile(display_name="Other learner")
    db.add(foreign)
    await db.flush()
    session = models.Session(learner_id=foreign.id, mode="steady", energy=3)
    db.add(session)
    await db.commit()
    path = f"/api/sessions/{session.id}"
    assert (await client.get(path + "/completion")).status_code == 404
    assert (await client.post(path + "/end", json={})).status_code == 404
    await db.refresh(session)
    assert session.ended_at is None


async def test_malformed_receipt_is_unverified(client, db):
    started = (await client.post("/api/sessions", json={})).json()
    sid = started["id"]
    s = await db.get(models.Session, sid)
    s.ended_at = utcnow_iso()
    db.add(
        models.LearningEvent(
            learner_id=s.learner_id,
            session_id=sid,
            actor="learner",
            verb="ended",
            object_type="session",
            object_id=sid,
            domain="meta",
            activity_type="recap",
            modality="text",
            mode="steady",
            energy=3,
            result_json={"notes": "Incomplete legacy record"},
        )
    )
    await db.commit()
    result = await client.get(f"/api/sessions/{sid}/completion")
    assert result.status_code == 200
    assert result.json()["status"] == "unverified"
    assert result.json()["recap"] is None
