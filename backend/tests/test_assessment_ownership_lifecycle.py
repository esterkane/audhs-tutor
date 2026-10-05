"""Real submission lifecycle with synthetic grading and disposable ownership storage."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.core.local_ownership import OwnershipUnavailable
from app.db import models
from app.models_ai.gateway import ModelGateway
from app.orchestrator import assessment_content, grader
from app.orchestrator.assessment_guard import AssessmentGuard
from tests.test_assessment_requests import HEADERS, prepare


async def model_question(client, db):
    body = await prepare(client, db)
    item = await db.get(models.Assessment, body["assessment_id"])
    item.kind = "explain_back"
    item.item_json = {"prompt": "Explain the mechanism"}
    await db.commit()
    body["content_version"] = assessment_content.token(
        await assessment_content.snapshot(db, item.id)
    )
    body["answer"] = "A mechanism with a causal explanation."
    return body


async def test_guard_held_through_learning_completion(client, db, db_path, monkeypatch):
    body = await prepare(client, db)
    original = grader.assessment_executions.mark_completed
    seen = []

    async def completing(session, learner, claim):
        row = await grader.assessment_executions.get_owned(session, learner, claim)
        seen.append(row.owner_json)
        assert AssessmentGuard.acquire_prepared(db_path, claim, row.owner_json) is None
        await original(session, learner, claim)

    monkeypatch.setattr(grader.assessment_executions, "mark_completed", completing)
    assert (await client.post("/api/assess/attempt", json=body, headers=HEADERS)).status_code == 200
    row = await db.scalar(select(models.AssessmentExecution))
    assert len(seen) == 1 and row.phase == "completed"
    # Deterministic grading does not seal: ownership alone never overrides SQL phase.
    guard = AssessmentGuard.acquire_prepared(db_path, row.claim_id, row.owner_json)
    assert guard is not None
    guard.close()


@pytest.mark.parametrize("cancel", [False, True])
async def test_gateway_observes_seal_and_finally_releases(client, db, db_path, monkeypatch, cancel):
    body = await model_question(client, db)
    seen = []

    async def fail(*args, **kwargs):
        row = await db.scalar(select(models.AssessmentExecution))
        await db.commit()
        assert row.phase == "inference_started" and row.owner_json
        assert AssessmentGuard.acquire_prepared(db_path, row.claim_id, row.owner_json) is None
        seen.append(row.claim_id)
        if cancel:
            raise asyncio.CancelledError()
        raise RuntimeError("lost acknowledgement")

    monkeypatch.setattr(ModelGateway, "complete", fail)
    with pytest.raises(RuntimeError):
        await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    row = await db.scalar(select(models.AssessmentExecution))
    # Unlocked now, but permanently sealed. A leaked live lock would return None instead.
    with pytest.raises(OwnershipUnavailable, match="may have entered inference"):
        AssessmentGuard.acquire_prepared(db_path, row.claim_id, row.owner_json)
    assert (await client.post("/api/assess/attempt", json=body, headers=HEADERS)).status_code == 409
    assert len(seen) == 1
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0


async def test_seal_failure_forbids_gateway_and_releases_new_claim(client, db, monkeypatch):
    body = await model_question(client, db)
    calls = []

    def fail(self):
        raise OSError("seal sync failed")

    async def gateway(*args, **kwargs):
        calls.append(True)
        raise AssertionError("must not enter gateway")

    monkeypatch.setattr(AssessmentGuard, "seal_inference", fail)
    monkeypatch.setattr(ModelGateway, "complete", gateway)
    with pytest.raises(OSError, match="seal sync failed"):
        await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert not calls
    assert await db.scalar(select(func.count()).select_from(models.WorkspaceRequest)) == 0
    assert await db.scalar(select(func.count()).select_from(models.AssessmentExecution)) == 0


async def test_unavailable_ownership_preserves_normal_grading(client, db, monkeypatch):
    body = await prepare(client, db)

    def unavailable(*args):
        raise OwnershipUnavailable("unsupported storage")

    monkeypatch.setattr(AssessmentGuard, "create", unavailable)
    assert (await client.post("/api/assess/attempt", json=body, headers=HEADERS)).status_code == 200
    row = await db.scalar(select(models.AssessmentExecution))
    assert row.phase == "completed" and row.owner_json is None
