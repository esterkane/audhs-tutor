from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db import models
from app.kernel import session as sessions
from app.kernel import skill_graph
from app.kernel.learner import get_or_create_owner
from app.kernel.seed import load_seed
from app.models_ai import registry
from app.schemas.common import Mode

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


@pytest.mark.parametrize("surface", ["turn", "stream"])
async def test_literal_and_saved_replay_do_not_initialize_retrieval(client, db, surface):
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags=set())
    owner = await get_or_create_owner(db)
    session = await sessions.start(db, owner.id, mode=Mode.STEADY, energy=3, socratic=True)
    skill = await skill_graph.next_skill(db, owner.id)
    await sessions.save_checkpoint(db, session, {"phase": "teach", "skill_id": skill.id})
    app = client._transport.app
    app.state.repo = None
    factory = Mock(side_effect=AssertionError("Unneeded retrieval must not initialize"))
    app.state.repo_factory = factory
    payload = {
        "session_id": session.id,
        "text": "Ask one question about `2 * 3`.",
        "action": "explain",
        "explanation_kind": "follow_up",
    }
    key = str(uuid4())
    first = await client.post(
        f"/api/tutor/{surface}", json=payload, headers={"Idempotency-Key": key}
    )
    assert first.status_code == 200, first.text
    replay = await client.post(
        f"/api/tutor/{surface}", json=payload, headers={"Idempotency-Key": key}
    )
    assert replay.status_code == 200, replay.text
    assert "what result would you expect?" in first.text
    assert "what result would you expect?" in replay.text
    factory.assert_not_called()
    answers = (
        await db.scalars(
            select(models.TutorAnswer).where(models.TutorAnswer.session_id == session.id)
        )
    ).all()
    assert len(answers) == 1
    checkpoint = await sessions.load_checkpoint(db, session.id)
    assert checkpoint["turn_id"] == answers[0].turn_id


@pytest.mark.parametrize("surface", ["turn", "stream"])
async def test_ordinary_explanation_still_requires_retrieval_and_reports_readiness(
    client, db, surface
):
    from app.models_ai.routing import NoModelReady

    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    owner = await get_or_create_owner(db)
    session = await sessions.start(db, owner.id, mode=Mode.STEADY, energy=3)
    skill = await skill_graph.next_skill(db, owner.id)
    await sessions.save_checkpoint(db, session, {"phase": "teach", "skill_id": skill.id})
    app = client._transport.app
    app.state.repo = None
    factory = Mock(side_effect=NoModelReady("synthetic embedding is not ready"))
    app.state.repo_factory = factory
    response = await client.post(
        f"/api/tutor/{surface}",
        json={"session_id": session.id, "text": "Explain the current concept", "action": "explain"},
    )
    assert response.status_code == (200 if surface == "stream" else 503)
    assert "no_model_ready" in response.text
    assert "synthetic embedding is not ready" in response.text
    factory.assert_called_once()
    assert not (
        await db.scalars(
            select(models.TutorAnswer).where(models.TutorAnswer.session_id == session.id)
        )
    ).all()


@pytest.mark.parametrize("surface", ["turn", "stream"])
async def test_saved_model_answer_replays_while_retrieval_is_unavailable(
    client, db, fake_local, surface
):
    import json

    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    owner = await get_or_create_owner(db)
    session = await sessions.start(db, owner.id, mode=Mode.STEADY, energy=3)
    skill = await skill_graph.next_skill(db, owner.id)
    await sessions.save_checkpoint(db, session, {"phase": "teach", "skill_id": skill.id})
    payload = {"session_id": session.id, "text": "Explain the current concept", "action": "explain"}
    key = str(uuid4())
    first = await client.post(
        f"/api/tutor/{surface}", json=payload, headers={"Idempotency-Key": key}
    )
    assert first.status_code == 200, first.text
    if surface == "stream":
        block = next(block for block in first.text.split("\n\n") if block.startswith("event: done"))
        before = json.loads(block.split("data: ", 1)[1])
    else:
        before = first.json()
    assert before["model_call_id"] and before["answer_id"]
    calls = len(fake_local.calls)
    app = client._transport.app
    app.state.repo = None
    factory = Mock(side_effect=AssertionError("Saved replay must not initialize retrieval"))
    app.state.repo_factory = factory
    replay = await client.post(
        f"/api/tutor/{surface}", json=payload, headers={"Idempotency-Key": key}
    )
    assert replay.status_code == 200, replay.text
    if surface == "stream":
        block = next(
            block for block in replay.text.split("\n\n") if block.startswith("event: done")
        )
        after = json.loads(block.split("data: ", 1)[1])
    else:
        after = replay.json()
    assert after == before
    factory.assert_not_called()
    assert len(fake_local.calls) == calls
    assert (
        len(
            (
                await db.scalars(
                    select(models.TutorAnswer).where(models.TutorAnswer.session_id == session.id)
                )
            ).all()
        )
        == 1
    )
