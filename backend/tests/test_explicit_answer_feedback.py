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


def test_feedback_uses_its_own_task_contract_and_keeps_current_answer_and_history():
    from app.orchestrator import playground, prompts

    body = PlaygroundRequest(
        session_id="s",
        intent="check_answer",
        exercise="Find the retained proportion",
        code="",
        learner_answer="I revised my answer: 60%.",
        history=[{"role": "assistant", "text": "The old answer was 90%."}],
    )
    packet = playground.messages(body)
    assert packet[0].content.count(prompts.answer_feedback_task()) == 1
    assert prompts.playground_task() not in packet[0].content
    assert "I revised my answer: 60%." in packet[1].content
    assert "The old answer was 90%." in packet[1].content
    assert "Selected questioning_style: explicit" in packet[1].content


async def test_wsl_feedback_routes_locally_without_an_override_or_hosted_fallback(
    client, db, fake_local
):
    await seed_defaults(db, installed_ollama_tags={"qwen3:14b"})
    app = client._transport.app
    app.state.settings = app.state.settings.model_copy(update={"routing_profile": "wsl"})
    assert Router("wsl").chain_for(TaskClass.ANSWER_FEEDBACK) == ["qwen3-14b"]
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    answer = "30/50 = 0.9"
    fake_local.structured = selection(answer)
    response = await client.post(
        "/api/playground/tutor",
        json={
            "session_id": session["id"],
            "intent": "check_answer",
            "exercise": "30 of 50 rows remain.",
            "code": "",
            "learner_answer": answer,
        },
    )
    assert response.status_code == 200, response.text
    assert fake_local.calls
    assert await db.scalar(select(func.count()).select_from(AssessmentAttempt)) == 0
    assert await db.scalar(select(func.count()).select_from(CompetencyEvidence)) == 0


def test_self_contradictory_correction_requires_repair_without_grading_the_answer():
    from app.schemas.feedback_selection import SelectionPoint

    base = {"passage_id": "p-example", "finding": "needs_revision"}
    with pytest.raises(ValidationError, match="correction repeats the same numeric value"):
        SelectionPoint(**base, explanation="30/40 equals 75%, not 75% as stated.")
    SelectionPoint(**base, explanation="30/40 equals 75%, not 90% as stated.")
    SelectionPoint(**base, explanation='Your claim "30/40 equals 75%, not 75%" contradicts itself.')
    SelectionPoint(
        **base, explanation="The rates are correct, but equal rules do not establish fairness."
    )


async def test_self_contradictory_feedback_is_repaired_before_it_is_saved(
    client, db, fake_local, monkeypatch
):
    import copy

    from app.models_ai.provider import structured_reason
    from app.schemas.feedback_selection import SelectionPoint

    body = await prepare(client, db)
    body["learner_answer"] = "A retains 90%, B retains 75%, a difference of 15 percentage points."
    good = selection(body["learner_answer"])
    good["points"][0].update(
        finding="supported", explanation="Both rates and the difference are correct."
    )
    original = fake_local.complete

    async def scripted(*args, **kwargs):
        fake_local.structured = copy.deepcopy(good)
        if not fake_local.calls:
            fake_local.structured["points"][0].update(
                finding="needs_revision", explanation="30/40 equals 75%, not 75% as stated."
            )
        return await original(*args, **kwargs)

    monkeypatch.setattr(fake_local, "complete", scripted)
    response = await client.post("/api/playground/tutor", json=body)
    assert response.status_code == 200, response.text
    assert len(fake_local.calls) == 2
    assert (
        "proposed numeric correction repeats the same value"
        in fake_local.calls[1].messages[-1].content
    )
    assert "75%, not 75%" not in response.json()["text"]
    with pytest.raises(ValidationError) as caught:
        SelectionPoint(
            passage_id="p", finding="needs_revision", explanation="30/40 equals 75%, not 75%."
        )
    assert structured_reason(caught.value) == "correction_unchanged"


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
