"""Real publication commands preserve existing learning and redirect future entry only."""

from copy import deepcopy
from uuid import uuid4

from sqlalchemy import select

from app.db import models
from app.kernel import memory
from tests.test_assessment_content_versions import prepare as assessment_setup
from tests.test_correction_validation import sourced_question
from tests.test_exercises import _node
from tests.test_review_content_versions import prepare as review_setup


async def attach_source(db, question):
    _, chunk, _ = await sourced_question(db)
    question.item_json = {**question.item_json, "source_chunk_id": chunk.id}
    await db.commit()


async def publish(client, question):
    report = await client.post(
        "/api/areas/feedback/questions",
        json={
            "assessment_id": question.id,
            "verdict": "bad",
            "labels": ["too_vague"],
            "note": "Synthetic correction",
        },
    )
    assert report.status_code == 200, report.text
    source = (await client.get(f"/api/questions/{question.id}/correction-source")).json()
    created = await client.post(
        "/api/questions/correction-drafts",
        json={
            "request_id": str(uuid4()),
            "assessment_id": question.id,
            "feedback_id": report.json()["id"],
            "expected_question_revision": source["question_revision"],
            "expected_content_version": source["content_version"],
        },
    )
    assert created.status_code == 200, created.text
    path = "/api/questions/correction-drafts/" + created.json()["draft_id"]
    candidate = deepcopy(source["candidate"])
    key = "question" if question.kind == "mcq" else "prompt"
    candidate["item"][key] += " Give a specific example."
    saved = await client.put(
        path, json={"request_id": str(uuid4()), "expected_revision": 1, "candidate": candidate}
    )
    assert saved.status_code == 200, saved.text
    preview = (await client.get(path + "/impact")).json()
    assert preview["publication_available"], preview
    result = await client.post(
        path + "/publish",
        json={
            "request_id": str(uuid4()),
            "expected_revision": 2,
            "preview_token": preview["preview_token"],
            "reviewed_sources": True,
        },
    )
    assert result.status_code == 200, result.text
    inbox = (await client.get("/api/questions/corrections")).json()
    assert report.json()["id"] not in [row["id"] for row in inbox["items"]]
    return result.json()["replacement_id"]


async def learning_snapshot(db):
    return {
        model.__tablename__: list((await db.execute(select(model.__table__))).mappings())
        for model in [
            models.AssessmentAttempt,
            models.CompetencyEvidence,
            models.CompetencyState,
            models.MemoryState,
            models.ReviewItem,
            models.ReviewLog,
        ]
    }


async def test_completed_grade_replays_and_new_old_question_submission_is_blocked(client, db):
    body = await assessment_setup(client, db)
    original = await db.get(models.Assessment, body["assessment_id"])
    await attach_source(db, original)
    shown = (
        await client.get(
            f"/api/assess/items/{original.id}", params={"session_id": body["session_id"]}
        )
    ).json()
    body["content_version"] = shown["content_version"]
    headers = {"Idempotency-Key": str(uuid4())}
    first = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert first.status_code == 200, first.text
    before = await learning_snapshot(db)
    replacement_id = await publish(client, original)
    assert replacement_id != original.id
    assert await learning_snapshot(db) == before
    replay = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert replay.status_code == 200 and replay.json() == first.json()
    rejected = await client.post(
        "/api/assess/attempt", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert rejected.status_code == 409
    assert await learning_snapshot(db) == before


async def test_queued_review_excluded_but_completed_rating_replays(client, db):
    item, original, body, _ = await review_setup(client, db, assessment=True)
    await attach_source(db, original)
    shown = (
        await client.get(f"/api/review/items/{item.id}", params={"session_id": body["session_id"]})
    ).json()
    body["content_version"] = shown["content_version"]
    headers = {"Idempotency-Key": str(uuid4())}
    first = await client.post(f"/api/review/{item.id}", json=body, headers=headers)
    assert first.status_code == 200, first.text
    queued, _ = await memory.ensure_item(
        db, item.learner_id, item.skill_id, "mcq", {"assessment_id": original.id}
    )
    await db.commit()
    assert queued.id != item.id
    assert queued.id in [row[0].id for row in await memory.due_items(db, item.learner_id)]
    before = await learning_snapshot(db)
    await publish(client, original)
    assert await learning_snapshot(db) == before
    assert queued.id not in [row[0].id for row in await memory.due_items(db, item.learner_id)]
    assert (
        await client.get(f"/api/review/items/{item.id}", params={"session_id": body["session_id"]})
    ).status_code == 404
    assert (
        await client.post(f"/api/review/{item.id}", json=body, headers=headers)
    ).json() == first.json()
    assert (
        await client.post(
            f"/api/review/{item.id}", json=body, headers={"Idempotency-Key": str(uuid4())}
        )
    ).status_code == 409
    assert await learning_snapshot(db) == before


async def test_published_linked_check_is_used_by_code_workspace(client, db):
    node = await _node(db)
    route = f"/api/exercises/for-skill/{node.id}"
    first = (await client.get(route)).json()
    original = await db.get(models.Assessment, first["check_assessment_id"])
    await attach_source(db, original)
    code = await db.get(models.Assessment, first["assessment_id"])
    preserved = deepcopy(code.item_json)
    before = await learning_snapshot(db)
    replacement_id = await publish(client, original)
    refreshed = await client.get(route)
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["check_assessment_id"] == replacement_id
    assert refreshed.json()["check_question"].endswith("Give a specific example.")
    assert refreshed.json()["starter_code"] == first["starter_code"]
    await db.refresh(code)
    assert code.item_json == preserved and await learning_snapshot(db) == before
