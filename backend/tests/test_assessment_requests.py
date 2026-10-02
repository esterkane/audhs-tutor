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


async def test_interruption_after_grading_never_regrades_uncertain_claim(client, db, monkeypatch):
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
    assert retry.status_code == 409
    found = await client.get(
        f"/api/assess/requests/{KEY}", params={"session_id": body["session_id"]}
    )
    assert found.json() == {"status": "unresolved", "result": None}
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
