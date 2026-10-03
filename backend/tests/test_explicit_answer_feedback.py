import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.db.models import (
    AssessmentAttempt,
    CompetencyEvidence,
    LearnerPreference,
    Session,
    TutorAnswer,
)
from app.models_ai.provider import TaskClass
from app.models_ai.registry import seed_defaults
from app.models_ai.routing import Router
from app.orchestrator.feedback_render import render_feedback
from app.schemas.feedback import bound_feedback
from app.schemas.feedback_selection import build_passages
from app.schemas.playground import PlaygroundRequest


def feedback(quote="30/50 = 0.9"):
    return {
        "points": [
            {
                "learner_quote": quote,
                "finding": "needs_revision",
                "explanation": "30 divided by 50 equals 0.6, or 60%.",
            }
        ],
        "next_step": "Use the starting row count as the denominator.",
        "followup_question": None,
    }


def selection(answer="30/50 = 0.9"):
    result = feedback()
    point = result["points"][0]
    del point["learner_quote"]
    point["passage_id"] = build_passages(answer)[0]["id"]
    return result


async def prepare(client, db):
    await seed_defaults(db, installed_ollama_tags={"gemma3:12b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    owner = await db.get(Session, session["id"])
    db.add(
        LearnerPreference(
            learner_id=owner.learner_id,
            key="routing.answer_feedback",
            origin="explicit",
            value_json="gemma3-12b",
        )
    )
    await db.commit()
    return {
        "session_id": session["id"],
        "intent": "check_answer",
        "exercise": "30 of 50 rows remain.",
        "code": "",
        "learner_answer": "30/50 = 0.9",
        "question": "Check my answer",
        "learning_context": {"target_id": "retention"},
    }


def test_blank_answer_rejected_and_route_is_scoped():
    for answer in (None, "", "  "):
        with pytest.raises(ValidationError):
            PlaygroundRequest(
                session_id="s",
                intent="check_answer",
                exercise="Task",
                code="",
                learner_answer=answer,
            )
    PlaygroundRequest(
        session_id="s",
        intent="check_answer",
        exercise="x" * 8000,
        code="",
        learner_answer="An answer",
    )
    with pytest.raises(ValidationError):
        PlaygroundRequest(
            session_id="s",
            intent="check_answer",
            exercise="x" * 8001,
            code="",
            learner_answer="An answer",
        )
    router = Router()
    assert router.chain_for(TaskClass.ANSWER_FEEDBACK) == ["openai-luna"]
    assert router.chain_for(TaskClass.EXPLAIN_SIMPLE)[0] == "gemma3-12b"


def test_quotes_cannot_create_active_markdown_and_labels_are_fallible():
    answer = "[click](https://example.com)\n<script>x</script>\n# heading"
    rendered = render_feedback(
        bound_feedback(answer, socratic=False).model_validate(feedback(answer))
    )
    assert "[click](https://example.com)" not in rendered
    assert "<script>" not in rendered
    assert "\n# heading" not in rendered
    assert "not a verified grade" in rendered


async def test_feedback_persists_exact_work_and_reuses_without_generation(client, db, fake_local):
    body = await prepare(client, db)
    fake_local.structured = selection(body["learner_answer"])
    result = await client.post("/api/playground/tutor", json=body)
    assert result.status_code == 200, result.text
    data = result.json()
    assert "You wrote:" in data["text"] and "Local arithmetic" in data["text"]
    row = await db.get(TutorAnswer, data["answer_id"])
    assert row.text == data["text"]
    assert row.metadata_json["quoted_feedback"] == feedback(body["learner_answer"])
    assert row.request_json["learner_answer"] == body["learner_answer"]
    again = await client.post("/api/playground/tutor", json={**body, "prefer_saved": True})
    assert again.status_code == 200 and again.json()["reused"]
    assert len(fake_local.calls) == 1
    fake_local.structured = selection("30/50 = 0.6")
    changed = await client.post(
        "/api/playground/tutor",
        json={**body, "prefer_saved": True, "learner_answer": "30/50 = 0.6"},
    )
    assert changed.status_code == 200 and not changed.json()["reused"]
    assert len(fake_local.calls) == 2
    assert await db.scalar(select(func.count()).select_from(AssessmentAttempt)) == 0
    assert await db.scalar(select(func.count()).select_from(CompetencyEvidence)) == 0


@pytest.mark.parametrize("bad", ["quote", "question", "transport"])
async def test_failed_feedback_never_saves_completed_reply(client, db, fake_local, bad):
    body = await prepare(client, db)
    fake_local.structured = selection(body["learner_answer"])
    if bad == "quote":
        fake_local.structured["points"][0]["passage_id"] = "not-a-current-passage"
    if bad == "question":
        fake_local.structured["followup_question"] = "Another question?"
    if bad == "transport":
        fake_local.fail_times = 10
    response = await client.post("/api/playground/tutor", json=body)
    assert response.status_code == 503, response.text
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 0


async def test_unavailable_scoped_provider_does_not_silently_use_general_model(
    client, db, fake_local
):
    await seed_defaults(db, installed_ollama_tags={"gemma3:12b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    response = await client.post(
        "/api/playground/tutor",
        json={
            "session_id": session["id"],
            "intent": "check_answer",
            "exercise": "Task",
            "code": "",
            "learner_answer": "An answer",
        },
    )
    assert response.status_code == 503
    assert not fake_local.calls


@pytest.mark.parametrize("unavailable", [True, False])
async def test_local_override_never_escalates_to_hosted(client, db, fake_local, unavailable):
    from app.db.models import ModelRegistry
    from app.models_ai.fake import FakeProvider

    body = await prepare(client, db)
    hosted = FakeProvider(structured=selection(body["learner_answer"]))
    client._transport.app.state.providers["openai"] = hosted
    row = await db.get(ModelRegistry, "openai-luna")
    row.status = "ready"
    if unavailable:
        local = await db.get(ModelRegistry, "gemma3-12b")
        local.status = "available"
    else:
        fake_local.fail_times = 10
    await db.commit()
    result = await client.post("/api/playground/tutor", json=body)
    assert result.status_code == 503
    assert not hosted.calls
