import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db import models
from app.kernel.seed import load_seed
from app.models_ai import registry
from app.orchestrator.grader import Grader

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"
KEY = "52b914ea-2562-4e73-821e-f25431583c87"
HEADERS = {"Idempotency-Key": KEY}


async def prepare(client, db):
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    item = (await client.get("/api/assess/next", params={"session_id": session["id"]})).json()[
        "item"
    ]
    return {
        "session_id": session["id"],
        "assessment_id": item["id"],
        "answer": "0",
        "content_version": item["content_version"],
    }


async def counts(db):
    return [
        await db.scalar(select(func.count()).select_from(t))
        for t in (
            models.AssessmentAttempt,
            models.CompetencyEvidence,
            models.LearningEvent,
            models.ModelCall,
            models.TutorAnswer,
        )
    ]


async def test_lost_response_replays_across_entrypoints_and_ended_session(
    client, db, fake_local, session_factory
):
    body = await prepare(client, db)
    lookup = f"/api/assess/requests/{KEY}"
    assert (await client.get(lookup, params={"session_id": body["session_id"]})).json()[
        "status"
    ] == "not_found"
    first = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert first.status_code == 200, first.text
    before = await counts(db)
    session = await db.get(models.Session, body["session_id"])
    session.ended_at = "2026-10-02T01:00:00Z"
    await db.commit()
    second = await client.post("/api/challenge/submit", json=body, headers=HEADERS)
    assert second.status_code == 200 and second.json() == first.json()
    found = await client.get(lookup, params={"session_id": body["session_id"]})
    assert found.json() == {"status": "completed", "result": first.json(), "saved_grade": None}
    from app.orchestrator.assessment_requests import lookup

    async with session_factory() as reopened:
        restored = await lookup(reopened, session.learner_id, session.id, KEY)
        assert (
            restored.result is not None and restored.result.model_dump(mode="json") == first.json()
        )

    conflict = await client.post(
        "/api/assess/attempt", json={**body, "answer": "1"}, headers=HEADERS
    )
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "request_conflict"
    assert await counts(db) == before
    assert fake_local.calls == []


async def test_concurrent_request_runs_one_grading_pipeline(client, db, monkeypatch):
    body = await prepare(client, db)
    entered, release = asyncio.Event(), asyncio.Event()
    original = Grader.grade

    async def delayed(self, request):
        entered.set()
        await release.wait()
        return await original(self, request)

    monkeypatch.setattr(Grader, "grade", delayed)
    first = asyncio.create_task(client.post("/api/assess/attempt", json=body, headers=HEADERS))
    await asyncio.wait_for(entered.wait(), 5)
    try:
        second = await client.post("/api/challenge/submit", json=body, headers=HEADERS)
        assert second.status_code == 409 and second.json()["error"]["code"] == "request_unresolved"
        assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0
    finally:
        release.set()
    assert (await first).status_code == 200
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 1
    assert await db.scalar(select(func.count()).select_from(models.CompetencyEvidence)) == 1


async def test_interruption_after_grading_recovers_completed_claim(client, db, monkeypatch):
    body = await prepare(client, db)
    original = Grader.grade

    async def interrupted(self, request):
        await original(self, request)
        raise asyncio.CancelledError()

    monkeypatch.setattr(Grader, "grade", interrupted)
    with pytest.raises(RuntimeError, match="No response returned"):
        await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    before = await counts(db)
    retry = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert retry.status_code == 200
    found = await client.get(
        f"/api/assess/requests/{KEY}", params={"session_id": body["session_id"]}
    )
    assert found.json() == {"status": "completed", "result": retry.json(), "saved_grade": None}
    assert await counts(db) == before
    assert before[0] == 1


async def test_lookup_is_owned_and_session_scoped(client, db):
    body = await prepare(client, db)
    assert (await client.post("/api/assess/attempt", json=body, headers=HEADERS)).status_code == 200
    owner_session = await db.get(models.Session, body["session_id"])
    another = models.Session(learner_id=owner_session.learner_id, mode="steady", energy=3)
    other = models.LearnerProfile(display_name="Other")
    db.add_all([another, other])
    await db.commit()
    foreign = models.Session(learner_id=other.id, mode="steady", energy=3)
    db.add(foreign)
    await db.commit()
    url = f"/api/assess/requests/{KEY}"
    assert (await client.get(url, params={"session_id": another.id})).json()[
        "status"
    ] == "not_found"
    errors = [await client.get(url, params={"session_id": sid}) for sid in (foreign.id, "missing")]
    assert all(r.status_code == 404 for r in errors)
    assert errors[0].json() == errors[1].json()


@pytest.mark.parametrize("after_history", [False, True])
async def test_committed_outcome_survives_history_interruption_and_restart(
    client,
    db,
    monkeypatch,
    session_factory,
    after_history,
):
    from app.core.answer_recovery import AnswerRecovery
    from app.orchestrator import grader

    body = await prepare(client, db)
    original = grader.save_feedback

    async def interrupted(*args, **kwargs):
        if after_history:
            await original(*args, **kwargs)
        raise asyncio.CancelledError()

    monkeypatch.setattr(grader, "save_feedback", interrupted)
    with pytest.raises(RuntimeError, match="No response returned"):
        await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    before = await counts(db)
    assert before[0:2] == [1, 1]
    assert await db.scalar(select(func.count()).select_from(models.ReviewLog)) == 1
    url = f"/api/assess/requests/{KEY}"
    first = (await client.get(url, params={"session_id": body["session_id"]})).json()
    assert first["status"] == "completed"
    assert bool(first["result"]["answer_id"]) == after_history
    # Process-local receipt signing key changes on restart, but the original snapshot is durable.
    client._transport.app.state.answer_recovery = AnswerRecovery()
    found = (await client.get(url, params={"session_id": body["session_id"]})).json()
    if not after_history:
        expired = await client.post(
            "/api/answers/recover-save", json={"receipt": first["result"]["save_receipt"]}
        )
        assert expired.status_code == 410
        # Editing the assessment cannot alter the historical snapshot used by recovery.
        assessment = await db.get(models.Assessment, body["assessment_id"])
        assessment.item_json = {**assessment.item_json, "question": "Changed after grading"}
        await db.commit()
        saved = await client.post(
            "/api/answers/recover-save", json={"receipt": found["result"]["save_receipt"]}
        )
        assert saved.status_code == 200
        detail = (await client.get("/api/answers/" + saved.json()["answer_id"])).json()
        assert detail["request"]["text"] != "Changed after grading"
    result = (await client.get(url, params={"session_id": body["session_id"]})).json()["result"]
    assert result["answer_id"] and result["save_error"] is None
    retry = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert retry.status_code == 200 and retry.json() == result
    after = await counts(db)
    assert after[:4] == before[:4]
    assert after[4] == 1
    async with session_factory() as reopened:
        claim = await reopened.scalar(select(models.WorkspaceRequest))
        assert claim.response_json["attempt_id"] == result["attempt_id"]
        assert "_assessment_history_v1" not in result


async def test_failure_completing_claim_rolls_back_learning_state(client, db, monkeypatch):
    from app.db import workspace_requests

    body = await prepare(client, db)
    before = await counts(db)
    original = workspace_requests.complete

    async def fail(*args, **kwargs):
        await original(*args, **kwargs)
        raise RuntimeError("before learning commit")

    monkeypatch.setattr(workspace_requests, "complete", fail)
    with pytest.raises(RuntimeError, match="before learning commit"):
        await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert await counts(db) == before
    found = await client.get(
        f"/api/assess/requests/{KEY}", params={"session_id": body["session_id"]}
    )
    assert found.json()["status"] == "grade_ready"
    assert found.json()["result"] is None
    assert found.json()["saved_grade"]["feedback"]
    monkeypatch.setattr(workspace_requests, "complete", original)

    async def no_regrading(*args, **kwargs):
        raise AssertionError("Recovery must not grade again")

    monkeypatch.setattr(Grader, "grade", no_regrading)
    results = await asyncio.gather(
        *[
            client.post(
                f"/api/assess/requests/{KEY}/finish", params={"session_id": body["session_id"]}
            )
            for _ in range(2)
        ]
    )
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    assert results[0].json()["attempt_id"] == results[1].json()["attempt_id"]
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 1


async def test_pre_inference_failure_releases_only_new_claim(client, db, monkeypatch):
    from app.orchestrator import grader

    body = await prepare(client, db)
    original = grader.grade_mcq

    def fail(*args):
        raise RuntimeError("before inference")

    monkeypatch.setattr(grader, "grade_mcq", fail)
    with pytest.raises(RuntimeError, match="before inference"):
        await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert await db.scalar(select(func.count()).select_from(models.WorkspaceRequest)) == 0
    monkeypatch.setattr(grader, "grade_mcq", original)
    assert (await client.post("/api/assess/attempt", json=body, headers=HEADERS)).status_code == 200
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 1


async def test_gateway_entry_failure_keeps_claim(client, db, monkeypatch):
    from app.models_ai.gateway import ModelGateway
    from app.orchestrator import assessment_content

    body = await prepare(client, db)
    item = await db.get(models.Assessment, body["assessment_id"])
    item.kind = "explain_back"
    item.item_json = {"prompt": "Explain the mechanism"}
    await db.commit()
    body["content_version"] = assessment_content.token(
        await assessment_content.snapshot(db, item.id)
    )
    body["answer"] = "A mechanism with a causal explanation."
    calls = []

    async def fail(*args, **kwargs):
        calls.append(True)
        raise RuntimeError("provider acknowledgement lost")

    monkeypatch.setattr(ModelGateway, "complete", fail)
    with pytest.raises(RuntimeError, match="provider acknowledgement lost"):
        await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    retry = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert retry.status_code == 409
    assert retry.json()["error"]["code"] == "request_unresolved"
    assert len(calls) == 1
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0


async def test_cleanup_failure_preserves_original_exception(client, db, monkeypatch):
    from app.db import workspace_requests
    from app.orchestrator import grader

    body = await prepare(client, db)

    def fail(*args):
        raise RuntimeError("original grading failure")

    async def cleanup_fail(*args):
        raise RuntimeError("cleanup unavailable")

    monkeypatch.setattr(grader, "grade_mcq", fail)
    monkeypatch.setattr(workspace_requests, "release_unstarted_assessment", cleanup_fail)
    with pytest.raises(RuntimeError, match="original grading failure"):
        await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    found = await client.get(
        f"/api/assess/requests/{KEY}", params={"session_id": body["session_id"]}
    )
    assert found.json()["status"] == "unresolved"


async def test_learning_commit_acknowledgement_loss_is_not_released(client, db, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    body = await prepare(client, db)
    original = AsyncSession.commit
    raised = []

    async def lost_ack(self):
        # Only fail the transaction containing the completed response, after commit.
        completed = await self.scalar(
            select(models.WorkspaceRequest).where(
                models.WorkspaceRequest.response_json.is_not(None)
            )
        )
        await original(self)
        if completed is not None and completed.response_json is not None and not raised:
            raised.append(True)
            raise RuntimeError("learning commit acknowledgement lost")

    monkeypatch.setattr(AsyncSession, "commit", lost_ack)
    with pytest.raises(RuntimeError, match="learning commit acknowledgement lost"):
        await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    monkeypatch.setattr(AsyncSession, "commit", original)
    retry = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert retry.status_code == 200
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 1
    assert await db.scalar(select(func.count()).select_from(models.CompetencyEvidence)) == 1


async def test_legacy_uncertain_claim_is_not_released(client, db, monkeypatch):
    from app.db import workspace_requests

    body = await prepare(client, db)
    session = await db.get(models.Session, body["session_id"])
    from app.schemas.grading import AttemptRequest

    await workspace_requests.claim(
        db,
        session.learner_id,
        session.id,
        "assessment:" + KEY,
        AttemptRequest.model_validate(body).model_dump(mode="json"),
    )

    async def never_grade(*args, **kwargs):
        raise AssertionError("legacy claim must not enter grading")

    monkeypatch.setattr(Grader, "grade", never_grade)
    result = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "request_unresolved"
    assert await db.scalar(select(func.count()).select_from(models.WorkspaceRequest)) == 1


async def test_pre_gateway_cancellation_remains_uncertain(client, db, monkeypatch):
    body = await prepare(client, db)

    async def cancel(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(Grader, "grade", cancel)
    with pytest.raises(RuntimeError, match="No response returned"):
        await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    found = await client.get(
        f"/api/assess/requests/{KEY}", params={"session_id": body["session_id"]}
    )
    assert found.json()["status"] == "unresolved"


async def test_old_cleanup_cannot_delete_replacement_or_completed_claim(client, db):
    from app.db import workspace_requests

    body = await prepare(client, db)
    session = await db.get(models.Session, body["session_id"])
    owner, sid = session.learner_id, session.id
    key = "assessment:" + KEY
    first, _ = await workspace_requests.claim(db, owner, sid, key, body)
    await workspace_requests.release_unstarted_assessment(db, owner, sid, key, first)
    replacement, _ = await workspace_requests.claim(db, owner, sid, key, body)
    await workspace_requests.release_unstarted_assessment(db, owner, sid, key, first)
    row = await db.get(models.WorkspaceRequest, replacement)
    assert row is not None
    await workspace_requests.complete(db, owner, replacement, {"completed": True})
    await workspace_requests.release_unstarted_assessment(db, owner, sid, key, replacement)
    await db.refresh(row)
    assert row.response_json == {"completed": True}
