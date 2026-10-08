"""Explicit continuation retains immutable work; uncertainty never permits inference."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.core import content_versions
from app.db import models
from app.orchestrator import grader
from app.orchestrator.assessment_guard import AssessmentGuard
from tests.test_assessment_requests import HEADERS, KEY, counts, prepare


async def staged(client, db, monkeypatch):
    body = await prepare(client, db)

    def interrupted(*args):
        raise asyncio.CancelledError()

    with monkeypatch.context() as patch:
        patch.setattr(grader, "grade_mcq", interrupted)
        with pytest.raises(RuntimeError, match="No response returned"):
            await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    row = await db.scalar(select(models.AssessmentExecution))
    assert row.phase == "prepared" and row.owner_json
    await db.commit()
    return body, row


def url(body, suffix=""):
    return f"/api/assess/requests/{KEY}{suffix}?session_id={body['session_id']}"


async def test_explicit_continuation_survives_token_rotation_and_replays(
    client, db, monkeypatch, fake_local
):
    body, row = await staged(client, db, monkeypatch)
    original = dict(row.request_json)
    before = await counts(db)
    monkeypatch.setattr(content_versions, "_KEY", b"new-process-key")
    state = await client.get(url(body))
    assert state.json()["status"] == "prepared_ready"
    assert await counts(db) == before and fake_local.calls == []
    assert (await client.post("/api/assess/attempt", json=body, headers=HEADERS)).status_code == 409
    done = await client.post(url(body, "/continue"))
    assert done.status_code == 200, done.text
    after = await counts(db)
    replay = await client.post(url(body, "/continue"))
    assert replay.json() == done.json()
    assert await counts(db) == after
    await db.refresh(row)
    assert row.request_json == original and row.phase == "completed"
    assert after[0:2] == [1, 1]


@pytest.mark.parametrize(
    "reason", ["busy", "sealed", "missing", "legacy", "changed", "ended", "tampered", "deleted"]
)
async def test_ineligible_request_never_continues(
    client, db, db_path, monkeypatch, fake_local, reason
):
    body, row = await staged(client, db, monkeypatch)
    held = None
    if reason in ("busy", "sealed"):
        held = AssessmentGuard.acquire_prepared(db_path, row.claim_id, row.owner_json)
        assert held is not None
        if reason == "sealed":
            held.seal_inference()
            held.close()
            held = None
    elif reason == "missing":
        (db_path.parent / f"{db_path.name}.assessment-locks" / row.claim_id).unlink()
    elif reason == "legacy":
        row.owner_json = None
    elif reason == "changed":
        item = await db.get(models.Assessment, body["assessment_id"])
        item.item_json = {**item.item_json, "question": "Changed"}
    elif reason == "ended":
        session = await db.get(models.Session, body["session_id"])
        session.ended_at = "2026-10-05T12:00:00Z"
    elif reason == "tampered":
        row.request_json = {**row.request_json, "answer": "different answer"}
    elif reason == "deleted":
        await db.delete(await db.get(models.Assessment, body["assessment_id"]))
    await db.commit()
    try:
        before = await counts(db)
        assert (await client.get(url(body))).json()["status"] == "unresolved"
        result = await client.post(url(body, "/continue"))
        assert result.status_code in (404, 409), result.text
        assert await counts(db) == before and fake_local.calls == []
        assert await db.scalar(select(func.count()).select_from(models.WorkspaceRequest)) == 1
    finally:
        if held:
            held.close()


async def test_concurrent_continuation_owns_one_execution(client, db, monkeypatch):
    body, _ = await staged(client, db, monkeypatch)
    entered, release = asyncio.Event(), asyncio.Event()
    original = grader.Grader.grade

    async def waiting(self, request):
        assert self.execution.prepared_continuation
        entered.set()
        await release.wait()
        return await original(self, request)

    monkeypatch.setattr(grader.Grader, "grade", waiting)
    first = asyncio.create_task(client.post(url(body, "/continue")))
    await asyncio.wait_for(entered.wait(), 5)
    try:
        assert (await client.get(url(body))).json()["status"] == "unresolved"
        assert (await client.post(url(body, "/continue"))).status_code == 409
    finally:
        release.set()
    assert (await first).status_code == 200
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 1
    assert await db.scalar(select(func.count()).select_from(models.CompetencyEvidence)) == 1


async def test_continue_scope_is_owned(client, db, monkeypatch):
    body, _ = await staged(client, db, monkeypatch)
    profile = models.LearnerProfile(display_name="Other")
    db.add(profile)
    await db.flush()
    foreign = models.Session(learner_id=profile.id, mode="steady", energy=3)
    db.add(foreign)
    await db.commit()
    assert (
        await client.post(url({**body, "session_id": foreign.id}, "/continue"))
    ).status_code == 404
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0


async def test_model_continuation_seals_before_gateway_and_cannot_repeat(
    client, db, db_path, monkeypatch
):
    from app.models_ai.gateway import ModelGateway
    from tests.test_assessment_ownership_lifecycle import model_question

    body = await model_question(client, db)
    original_prepare = grader.assessment_executions.prepare

    async def stop_after_prepare(*args, **kwargs):
        await original_prepare(*args, **kwargs)
        raise asyncio.CancelledError()

    with monkeypatch.context() as patch:
        patch.setattr(grader.assessment_executions, "prepare", stop_after_prepare)
        with pytest.raises(RuntimeError, match="No response returned"):
            await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    calls = []

    async def uncertain(*args, **kwargs):
        row = await db.scalar(select(models.AssessmentExecution))
        assert row.phase == "inference_started"
        assert AssessmentGuard.acquire_prepared(db_path, row.claim_id, row.owner_json) is None
        calls.append(True)
        await db.commit()
        raise RuntimeError("Provider outcome unknown")

    monkeypatch.setattr(ModelGateway, "complete", uncertain)
    assert (await client.get(url(body))).json()["status"] == "prepared_ready"
    with pytest.raises(RuntimeError, match="Provider outcome unknown"):
        await client.post(url(body, "/continue"))
    assert (await client.get(url(body))).json()["status"] == "unresolved"
    assert (await client.post(url(body, "/continue"))).status_code == 409
    assert calls == [True]
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0
