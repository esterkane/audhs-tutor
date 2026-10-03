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
    return {"session_id": session["id"], "assessment_id": item["id"], "answer": "0"}


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
    assert found.json() == {"status": "completed", "result": first.json()}
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
    assert found.json() == {"status": "completed", "result": retry.json()}
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
    assert found.json() == {"status": "unresolved", "result": None}
