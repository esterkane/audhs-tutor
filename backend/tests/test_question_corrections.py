"""Read-only owned correction discovery; no hidden keys or evidence mutations."""

from sqlalchemy import func, select

from app.db import models
from tests.test_assessment_content_versions import prepare


async def test_latest_report_projection_and_withdrawal(client, db):
    body = await prepare(client, db)
    a = await db.get(models.Assessment, body["assessment_id"])
    payload = {
        "assessment_id": a.id,
        "verdict": "bad",
        "labels": ["incorrect"],
        "note": "Check this",
    }
    first = await client.post("/api/areas/feedback/questions", json=payload)
    assert first.status_code == 200, first.text
    report = (await client.get("/api/questions/corrections")).json()
    assert report["total"] == 1
    item = report["items"][0]
    assert item["content_status"] == "unchanged" and item["note"] == "Check this"
    assert set(item) == {
        "id",
        "target",
        "assessment_id",
        "draft_id",
        "reported_question",
        "current_question",
        "content_status",
        "labels",
        "note",
        "created_at",
    }
    second = await client.post("/api/areas/feedback/questions", json={**payload, "verdict": "good"})
    assert (await client.get("/api/questions/corrections")).json()["total"] == 0
    await client.delete("/api/areas/feedback/questions/" + second.json()["id"])
    assert (await client.get("/api/questions/corrections")).json()["items"][0][
        "id"
    ] == first.json()["id"]
    a.item_json = {**a.item_json, "question": "Changed wording", "answer": "SECRET-ANSWER"}
    await db.commit()
    response = await client.get("/api/questions/corrections")
    assert response.json()["items"][0]["content_status"] == "changed"
    assert response.json()["items"][0]["current_question"] == "Changed wording"
    assert "SECRET-ANSWER" not in response.text
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0
    assert await db.scalar(select(func.count()).select_from(models.QuestionState)) == 0


async def test_owned_pagination_and_unavailable_targets(client, db):
    body = await prepare(client, db)
    session = await db.get(models.Session, body["session_id"])
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.flush()
    for i in range(4):
        db.add(
            models.QuestionFeedback(
                learner_id=session.learner_id if i < 3 else other.id,
                target_key=f"missing:{i}",
                verdict="bad",
                labels_json=["incorrect"],
                note=f"note{i}",
                snapshot_json={"item": {"question": f"Question {i}", "answer": "SECRET"}},
            )
        )
    await db.commit()
    first = (await client.get("/api/questions/corrections?limit=2")).json()
    second = (await client.get("/api/questions/corrections?limit=2&offset=2")).json()
    assert first["total"] == second["total"] == 3
    assert len(first["items"]) == 2 and len(second["items"]) == 1
    assert len({i["id"] for i in first["items"] + second["items"]}) == 3
    assert all(i["content_status"] == "unavailable" for i in first["items"] + second["items"])
    assert "note3" not in str(first) + str(second)
    assert (await client.get("/api/questions/corrections?limit=51")).status_code == 422
    assert (await client.get("/api/questions/corrections?offset=-1")).status_code == 422


async def test_draft_snapshot_is_not_guessed_after_edit(client, db):
    body = await prepare(client, db)
    session = await db.get(models.Session, body["session_id"])
    snapshot = {"kind": "cloze", "item": {"question": "Original draft wording", "answer": "SECRET"}}
    draft = models.CurriculumDraft(
        learner_id=session.learner_id,
        title="Synthetic draft",
        payload_json={"assessments": [snapshot]},
        version=1,
    )
    db.add(draft)
    await db.commit()
    response = await client.post(
        "/api/areas/feedback/questions",
        json={
            "draft_id": draft.id,
            "draft_version": 1,
            "question_index": 0,
            "verdict": "bad",
            "labels": ["too_vague"],
        },
    )
    assert response.status_code == 200
    result = (await client.get("/api/questions/corrections")).json()["items"][0]
    assert result["target"] == "draft" and result["content_status"] == "unchanged"
    assert result["reported_question"] == "Original draft wording"
    draft.version = 2
    draft.payload_json = {"assessments": [{"item": {"question": "Unrelated replacement"}}]}
    await db.commit()
    changed = await client.get("/api/questions/corrections")
    result = changed.json()["items"][0]
    assert result["content_status"] == "changed" and result["current_question"] is None
    assert "Unrelated replacement" not in changed.text and "SECRET" not in changed.text
