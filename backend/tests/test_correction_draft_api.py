from uuid import uuid4

from sqlalchemy import func, select

from app.core import content_versions
from app.db import models
from app.kernel import correction_drafts
from app.schemas.correction_drafts import CreateCorrectionDraft
from tests.test_assessment_content_versions import prepare


async def source(client, db):
    body = await prepare(client, db)
    response = await client.get(f"/api/questions/{body['assessment_id']}/correction-source")
    assert response.status_code == 200
    result = response.json()
    assert result["contains_reference_answers"] is True
    assert "source_evidence" not in result and "original_fingerprint" not in result
    return result


def creation(view):
    return {
        "request_id": str(uuid4()),
        "assessment_id": view["assessment_id"],
        "expected_question_revision": view["question_revision"],
        "expected_content_version": view["content_version"],
    }


async def test_save_recover_discard_and_replay_after_restart(client, db, monkeypatch):
    view = await source(client, db)
    command = creation(view)
    response = await client.post("/api/questions/correction-drafts", json=command)
    assert response.status_code == 200, response.text
    first = response.json()
    path = "/api/questions/correction-drafts/" + first["draft_id"]
    save = {
        "request_id": str(uuid4()),
        "expected_revision": 1,
        "candidate": {"item": {}, "rubric": None},
        "rationale": "Incomplete work, keep it",
    }
    saved = await client.put(path, json=save)
    assert saved.status_code == 200 and saved.json()["revision"] == 2
    monkeypatch.setattr(content_versions, "_KEY", b"restarted-process-key")
    assert (await client.post("/api/questions/correction-drafts", json=command)).json() == first
    recovered = await client.get("/api/questions/correction-commands/" + save["request_id"])
    assert recovered.json() == saved.json()
    draft = (await client.get(path)).json()
    assert draft["revision"] == 2 and draft["candidate"] == save["candidate"]
    assert draft["review"]["problems"] and not draft["review"]["publication_available"]
    assert draft["original_candidate"] == view["candidate"]
    discarded = await client.post(
        path + "/discard", json={"request_id": str(uuid4()), "expected_revision": 2}
    )
    assert discarded.status_code == 200 and discarded.json()["status"] == "discarded"
    assert (await client.put(path, json=save)).json() == saved.json()
    assert (await client.get(path)).json()["status"] == "discarded"
    listing = (await client.get("/api/questions/correction-drafts")).json()
    assert listing["total"] == 1 and "candidate" not in listing["items"][0]
    for table in [models.AssessmentAttempt, models.CompetencyEvidence, models.QuestionState]:
        assert await db.scalar(select(func.count()).select_from(table)) == 0


async def test_stale_create_and_changed_request_do_not_write(client, db):
    view = await source(client, db)
    command = creation(view)
    assessment = await db.get(models.Assessment, view["assessment_id"])
    assessment.item_json = {**assessment.item_json, "explanation": "Changed explanation"}
    await db.commit()
    stale = await client.post("/api/questions/correction-drafts", json=command)
    assert stale.status_code == 409
    assert await db.scalar(select(func.count()).select_from(models.QuestionCorrectionCommand)) == 0
    fresh = (await client.get(f"/api/questions/{assessment.id}/correction-source")).json()
    command = creation(fresh)
    first = await client.post("/api/questions/correction-drafts", json=command)
    assert first.status_code == 200
    changed = await client.post(
        "/api/questions/correction-drafts", json={**command, "expected_question_revision": 5}
    )
    assert changed.status_code == 409
    missing = await client.get("/api/questions/correction-commands/" + str(uuid4()))
    assert (
        missing.status_code == 404 and "may still be running" in missing.json()["error"]["message"]
    )
    assert (
        await client.post(
            "/api/questions/correction-drafts",
            json={k: v for k, v in command.items() if k != "expected_content_version"},
        )
    ).status_code == 422


async def test_other_learner_cannot_read_save_discard_or_recover_draft(client, db):
    view = await source(client, db)
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    command = CreateCorrectionDraft(
        request_id=uuid4(), assessment_id=view["assessment_id"], expected_question_revision=0
    )
    result = await correction_drafts.create(db, other.id, command)
    await db.commit()
    path = "/api/questions/correction-drafts/" + result.draft_id
    assert (await client.get(path)).status_code == 404
    assert (
        await client.get("/api/questions/correction-commands/" + str(command.request_id))
    ).status_code == 404
    assert (await client.get("/api/questions/correction-drafts")).json()["total"] == 0
    assert (
        await client.put(
            path, json={"request_id": str(uuid4()), "expected_revision": 1, "candidate": {}}
        )
    ).status_code == 404
    assert (
        await client.post(
            path + "/discard", json={"request_id": str(uuid4()), "expected_revision": 1}
        )
    ).status_code == 404
    assert (await client.get("/api/questions/correction-drafts?limit=51")).status_code == 422


async def test_malformed_token_is_validation_error_not_server_error(client, db):
    view = await source(client, db)
    response = await client.post(
        "/api/questions/correction-drafts",
        json={
            **creation(view),
            "expected_content_version": "non-ascii-ä",
        },
    )
    assert response.status_code == 422
    assert await db.scalar(select(func.count()).select_from(models.QuestionCorrectionDraft)) == 0
