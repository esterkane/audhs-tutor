"""Explicit eligibility controls: preview, repeat-safe writes and owned discovery."""

from uuid import uuid4

from sqlalchemy import func, select

from app.db import models
from app.kernel import memory
from tests.test_assessment_content_versions import prepare


async def test_preview_transition_retry_and_restore(client, db):
    body = await prepare(client, db)
    a = await db.get(models.Assessment, body["assessment_id"])
    s = await db.get(models.Session, body["session_id"])
    await memory.ensure_item(db, s.learner_id, a.skill_id, a.kind, {"ref": a.id})
    path = f"/api/questions/{a.id}/practice"
    preview = (await client.get(path)).json()
    assert preview["affected_reviews"] == 1 and preview["status"]["revision"] == 0
    assert set(preview) == {"status", "skill_title", "question", "affected_reviews"}
    request = {
        "request_id": str(uuid4()),
        "expected_revision": 0,
        "action": "suspend",
        "reason": "Wrong context",
    }
    first = await client.post(path, json=request)
    assert first.status_code == 200 and first.json()["state"] == "suspended"
    assert (await client.post(path, json=request)).json() == first.json()
    listing = (await client.get("/api/questions/excluded")).json()
    assert listing["total"] == 1 and listing["items"][0]["status"]["reason"] == "Wrong context"
    stale = await client.post(path, json={**request, "request_id": str(uuid4())})
    assert stale.status_code == 409
    restored = await client.post(
        path, json={"request_id": str(uuid4()), "expected_revision": 1, "action": "restore"}
    )
    assert restored.status_code == 200 and restored.json()["state"] == "active"
    assert (await client.get("/api/questions/excluded")).json()["total"] == 0
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0
    assert await db.scalar(select(func.count()).select_from(models.QuestionTransition)) == 2


async def test_preview_does_not_include_other_learners_cards_or_vocab(client, db):
    body = await prepare(client, db)
    a = await db.get(models.Assessment, body["assessment_id"])
    s = await db.get(models.Session, body["session_id"])
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    await memory.ensure_item(db, other.id, a.skill_id, a.kind, {"ref": a.id})
    await memory.ensure_item(db, s.learner_id, a.skill_id, "vocab", {"type": "vocab", "ref": a.id})
    result = (await client.get(f"/api/questions/{a.id}/practice")).json()
    assert result["affected_reviews"] == 0
    assert (await client.get("/api/questions/excluded?limit=0")).status_code == 422
    assert (await client.get("/api/questions/missing/practice")).status_code == 404
