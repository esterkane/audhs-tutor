"""Answer-producing routes cannot use another learner's session."""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.kernel.seed import load_seed
from app.models_ai import registry
from app.models_ai.fake import FakeProvider

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


@pytest.mark.parametrize("surface", ["turn", "stream", "representation", "prefer"])
async def test_foreign_session_is_indistinguishable_from_missing(
    client: AsyncClient, db: AsyncSession, fake_local: FakeProvider, surface: str
) -> None:
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    await client.get("/api/learner/me")
    other = models.LearnerProfile(display_name="Other learner")
    db.add(other)
    await db.commit()
    foreign = models.Session(learner_id=other.id, mode="steady", energy=3)
    db.add(foreign)
    await db.commit()
    responses = []
    for sid in (foreign.id, "missing"):
        if surface in ("turn", "stream"):
            url = f"/api/tutor/{surface}"
            payload = {"session_id": sid, "text": "Explain this"}
        elif surface == "representation":
            url = "/api/objects/example/representations/analogy"
            payload = {"session_id": sid}
        else:
            url = "/api/objects/example/representations/prefer"
            payload = {"session_id": sid, "chosen_id": "a", "rejected_id": "b"}
        response = await client.post(url, json=payload)
        if surface == "stream":
            assert response.status_code == 200
            events = [block for block in response.text.strip().split("\n\n") if block]
            assert len(events) == 1 and events[0].startswith("event: error\n")
            data = json.loads(events[0].split("data: ", 1)[1])
        else:
            assert response.status_code == 404, response.text
            data = response.json()["error"]
        responses.append(data)
    assert responses[0] == responses[1]
    assert fake_local.calls == []
    for table in (
        models.TutorTrace,
        models.ModelCall,
        models.LearningEvent,
        models.SessionCheckpoint,
    ):
        assert await db.scalar(select(func.count()).select_from(table)) == 0


@pytest.mark.parametrize("surface", ["next", "attempt", "challenge_start", "challenge_submit"])
async def test_assessment_rejects_foreign_session_before_generation_or_grading(
    client: AsyncClient, db: AsyncSession, fake_local: FakeProvider, surface: str
) -> None:
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    owner_session = (
        await client.post("/api/sessions", json={"mode": "steady", "energy": 3})
    ).json()
    skill_id = owner_session["next_skill"]["id"]
    item_response = await client.get(
        "/api/assess/next", params={"session_id": owner_session["id"], "skill_id": skill_id}
    )
    assert item_response.status_code == 200
    item = item_response.json()["item"]
    other = models.LearnerProfile(display_name="Other learner")
    db.add(other)
    await db.commit()
    foreign = models.Session(learner_id=other.id, mode="steady", energy=3)
    db.add(foreign)
    await db.commit()
    tables = (
        models.AssessmentAttempt,
        models.CompetencyEvidence,
        models.MemoryState,
        models.LearningEvent,
        models.ModelCall,
        models.TutorAnswer,
    )
    counts = [await db.scalar(select(func.count()).select_from(table)) for table in tables]
    calls = len(fake_local.calls)
    errors = []
    for session_id in (foreign.id, "missing"):
        if surface == "next":
            result = await client.get(
                "/api/assess/next", params={"session_id": session_id, "skill_id": skill_id}
            )
        elif surface == "challenge_start":
            result = await client.post(
                "/api/challenge/start",
                json={"session_id": session_id, "skill_id": skill_id, "mode": "planted_error"},
            )
        else:
            result = await client.post(
                "/api/challenge/submit" if surface == "challenge_submit" else "/api/assess/attempt",
                json={"session_id": session_id, "assessment_id": item["id"], "answer": "0"},
            )
        assert result.status_code == 404, result.text
        errors.append(result.json())
    assert errors[0] == errors[1]
    assert len(fake_local.calls) == calls
    assert counts == [await db.scalar(select(func.count()).select_from(table)) for table in tables]
