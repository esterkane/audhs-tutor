"""Explicit durable-result recovery never repeats grading or loses original identity."""

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, func, select

from app.core import content_versions
from app.db import models, workspace_requests
from app.orchestrator import assessment_content
from app.orchestrator.grader import Grader
from tests.test_assessment_requests import HEADERS, KEY, counts, prepare


async def stage_failed(client, db, monkeypatch):
    body = await prepare(client, db)
    original = workspace_requests.complete

    async def fail(*args, **kwargs):
        await original(*args, **kwargs)
        raise RuntimeError("staged before failed learning commit")

    with monkeypatch.context() as patch:
        patch.setattr(workspace_requests, "complete", fail)
        with pytest.raises(RuntimeError, match="staged before failed learning commit"):
            await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0
    return body


async def finish(client, body):
    return await client.post(
        f"/api/assess/requests/{KEY}/finish", params={"session_id": body["session_id"]}
    )


async def test_finish_after_public_key_rotation_and_ended_session(
    client, db, monkeypatch, fake_local
):
    body = await stage_failed(client, db, monkeypatch)
    monkeypatch.setattr(content_versions, "_KEY", b"replacement-public-token-secret")
    fresh = assessment_content.token(await assessment_content.snapshot(db, body["assessment_id"]))
    assert fresh != body["content_version"]
    session = await db.get(models.Session, body["session_id"])
    session.ended_at = datetime.now(UTC).isoformat()
    await db.commit()

    async def never_grade(*args, **kwargs):
        raise AssertionError("Finishing must not invoke grading")

    monkeypatch.setattr(Grader, "grade", never_grade)
    result = await finish(client, body)
    assert result.status_code == 200, result.text
    before = await counts(db)
    replay = await finish(client, body)
    assert replay.status_code == 200
    assert replay.json()["attempt_id"] == result.json()["attempt_id"]
    assert await counts(db) == before
    assert fake_local.calls == []


@pytest.mark.parametrize("deleted", [False, True])
async def test_changed_or_deleted_content_keeps_staged_grade_without_evidence(
    client, db, monkeypatch, deleted
):
    body = await stage_failed(client, db, monkeypatch)
    before = await counts(db)
    if deleted:
        await db.execute(
            delete(models.Assessment).where(models.Assessment.id == body["assessment_id"])
        )
    else:
        item = await db.get(models.Assessment, body["assessment_id"])
        item.item_json = {**item.item_json, "question": "Changed after staging"}
    await db.commit()
    result = await finish(client, body)
    assert result.status_code == (404 if deleted else 409), result.text
    assert await counts(db) == before
    staged = await db.scalar(select(models.AssessmentExecution))
    assert staged.phase == "grade_ready" and staged.grade_json
    claim = await db.get(models.WorkspaceRequest, staged.claim_id)
    assert claim.response_json is None
    preview = await client.get(
        f"/api/assess/requests/{KEY}", params={"session_id": body["session_id"]}
    )
    assert preview.status_code == 200
    assert preview.json()["status"] == "grade_ready"
    assert preview.json()["saved_grade"] == staged.grade_json["result"]
    assert preview.json()["result"] is None
    assert await counts(db) == before


async def test_finish_rejects_wrong_session_and_owner(client, db, monkeypatch):
    body = await stage_failed(client, db, monkeypatch)
    owner_session = await db.get(models.Session, body["session_id"])
    other = models.LearnerProfile(display_name="Other")
    another = models.Session(learner_id=owner_session.learner_id, mode="steady", energy=3)
    db.add_all([other, another])
    await db.commit()
    foreign = models.Session(learner_id=other.id, mode="steady", energy=3)
    db.add(foreign)
    await db.commit()
    before = await counts(db)
    for session_id in (another.id, foreign.id, "missing"):
        response = await finish(client, {**body, "session_id": session_id})
        assert response.status_code == 404
    assert await counts(db) == before
    assert (await db.scalar(select(models.AssessmentExecution))).phase == "grade_ready"


async def test_original_apply_races_explicit_finish_once(client, db, monkeypatch):
    body = await prepare(client, db)
    staged, release = asyncio.Event(), asyncio.Event()
    original = Grader.apply_result
    intercepted = False

    async def pause_original(self, *args, **kwargs):
        nonlocal intercepted
        if not intercepted:
            intercepted = True
            staged.set()
            await asyncio.wait_for(release.wait(), 10)
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(Grader, "apply_result", pause_original)
    pending = asyncio.create_task(client.post("/api/assess/attempt", json=body, headers=HEADERS))
    await asyncio.wait_for(staged.wait(), 5)
    try:
        recovered = await finish(client, body)
        assert recovered.status_code == 200, recovered.text
    finally:
        release.set()
    initial = await pending
    assert initial.status_code == 200, initial.text
    assert initial.json()["attempt_id"] == recovered.json()["attempt_id"]
    for table in (models.AssessmentAttempt, models.CompetencyEvidence, models.ReviewLog):
        assert await db.scalar(select(func.count()).select_from(table)) == 1


async def test_recovery_preserves_original_grading_time(client, db, monkeypatch):
    from fsrs import Card, Scheduler

    from app.kernel import memory

    monkeypatch.setattr(memory, "scheduler", lambda: Scheduler(enable_fuzzing=False))
    original = Grader.grade
    graded_at = datetime(2026, 9, 1, 12, 30, tzinfo=UTC)

    async def fixed_time(self, body):
        return await original(self, body, now=graded_at)

    monkeypatch.setattr(Grader, "grade", fixed_time)
    body = await stage_failed(client, db, monkeypatch)
    staged = await db.scalar(select(models.AssessmentExecution))
    assert datetime.fromisoformat(staged.grade_json["graded_at"]) == graded_at
    result = await finish(client, body)
    assert result.status_code == 200, result.text
    log = await db.scalar(select(models.ReviewLog))
    state = await db.scalar(
        select(models.MemoryState).where(models.MemoryState.review_item_id == log.review_item_id)
    )
    assert datetime.fromisoformat(log.reviewed_at) == graded_at
    assert datetime.fromisoformat(state.last_review) == graded_at
    expected, _ = memory.scheduler().review_card(
        Card(due=graded_at),
        memory.rating_from_score(result.json()["score"]),
        review_datetime=graded_at,
    )
    assert datetime.fromisoformat(state.due) == expected.due
