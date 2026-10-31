from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import models
from app.kernel import session as sessions
from app.kernel import skill_graph
from app.kernel.learner import get_or_create_owner
from app.kernel.seed import load_seed
from app.models_ai import registry
from app.orchestrator.context import SectionBudget, build_packet, render_messages
from app.schemas.common import Mode

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"
TAIL = "\nAlso distinguish Repeatable Read from Serializable, and say whether retry guarantees success."


def question(length):
    return ("Context: ä → `value` | " * 250)[: length - len(TAIL)] + TAIL


@pytest.mark.parametrize("length", [1601, 2400, 3999, 4000])
def test_default_packet_preserves_every_valid_request_character(length):
    text = question(length)
    assert len(text) == length
    packet = build_packet(policy="P", request=text, prompt_version="test")
    assert packet.request == text
    assert "request:truncated" not in packet.dropped
    assert text in render_messages(packet)[1].content


@pytest.mark.parametrize("surface", ["turn", "stream"])
async def test_full_question_reaches_provider_and_remains_in_saved_history(
    client, db, fake_local, surface
):
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    owner = await get_or_create_owner(db)
    session = await sessions.start(db, owner.id, mode=Mode.STEADY, energy=3)
    skill = await skill_graph.next_skill(db, owner.id)
    await sessions.save_checkpoint(db, session, {"phase": "teach", "skill_id": skill.id})
    text = question(4000)
    response = await client.post(
        f"/api/tutor/{surface}",
        json={
            "session_id": session.id,
            "text": text,
            "action": "explain",
            "explanation_kind": "follow_up",
        },
    )
    assert response.status_code == 200, response.text
    assert len(fake_local.calls) == 1
    assert text in fake_local.calls[0].messages[-1].content
    saved = await db.scalar(
        select(models.TutorAnswer).where(models.TutorAnswer.session_id == session.id)
    )
    assert saved.request_json["text"] == text
    trace = await db.scalar(
        select(models.TutorTrace).where(models.TutorTrace.turn_id == saved.turn_id)
    )
    assert "request:truncated" not in trace.dropped_json


async def test_api_still_rejects_questions_above_existing_limit(client, fake_local):
    response = await client.post(
        "/api/tutor/turn", json={"session_id": "unused", "text": "x" * 4001}
    )
    assert response.status_code == 422
    assert fake_local.calls == []


def test_short_questions_keep_identical_messages_and_other_context_sections():
    arguments = dict(
        policy="stable policy",
        request=question(1200),
        prompt_version="v",
        learning_contract={"objective": "A complete objective", "examples": ["An example"]},
        preferences={"tutor.response_language": "de"},
    )
    previous = build_packet(**arguments, budget=SectionBudget(request=400))
    current = build_packet(**arguments)
    assert current.model_dump() == previous.model_dump()
    assert render_messages(current) == render_messages(previous)


def test_explicit_smaller_packet_budget_still_bounds_and_reports_truncation():
    text = question(1000)
    packet = build_packet(
        policy="P", request=text, prompt_version="v", budget=SectionBudget(request=20)
    )
    assert len(packet.request) <= 80
    assert packet.request.endswith("…")
    assert "request:truncated" in packet.dropped
