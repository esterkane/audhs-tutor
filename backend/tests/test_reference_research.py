import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.db.models import ModelCall
from app.models_ai import registry
from app.orchestrator import reference_research
from app.orchestrator.personas import TutorPresentation
from app.schemas.knowledge_authoring import ResearchQuestion, ResearchTutorExchange

SOURCE = "In Python, strings are immutable. text = 'go'; result = text * 1."
QUERY = "Does immutability guarantee a new object? Distinguish == and is."


def question(**changes):
    return ResearchQuestion(
        id="q", prompt=QUERY, findings="Immutability guarantees a new object.", **changes
    )


@pytest.mark.parametrize("language", ["en", "de", "unchanged"])
def test_reviewed_reference_is_bilingual_and_not_a_runtime_prediction(language):
    answer = reference_research.answer(
        SOURCE, question(), TutorPresentation(persona="none", language=language)
    )
    assert answer and answer.source_quotes == [SOURCE, reference_research.REFERENCE]
    assert reference_research.URL in answer.source_quotes[1]
    assert "==" in answer.discussion and "is" in answer.discussion
    assert answer.discussion.startswith("Nein." if language == "de" else "No.")
    assert not answer.section


@pytest.mark.parametrize(
    "query",
    [
        "Does immutability guarantee a new object? Also calculate the value.",
        "Does immutability guarantee a new object? Run id(text).",
        "Explain list aliasing.",
        "Does immutability guarantee a new object and why did I make this mistake?",
    ],
)
def test_broader_requests_defer_without_being_partially_answered(query):
    assert (
        reference_research.answer(SOURCE, question(tutor_request=query), TutorPresentation())
        is None
    )


@pytest.mark.parametrize(
    "change", ["memory", "unresolved", "other-language", "long", "no-strings", "subclass"]
)
def test_unrelated_or_extra_context_keeps_normal_model_path(change):
    passage = SOURCE
    changes = {}
    if change == "memory":
        changes["memory_ids"] = ["0" * 64]
    elif change == "unresolved":
        changes["unresolved"] = "What about another type?"
    elif change == "other-language":
        passage = "JavaScript strings are immutable."
    elif change == "long":
        passage += "x" * 1800
    elif change == "subclass":
        passage = "Python string subclass with custom __eq__."
    else:
        passage = "Python integers."
    assert reference_research.answer(passage, question(**changes), TutorPresentation()) is None


def test_recovery_rejects_mixed_generation_identities():
    answer = reference_research.answer(SOURCE, question(), TutorPresentation())
    assert answer
    for extra in [{"model_call_id": "call"}, {"calculation": "python.string-repetition.v1"}]:
        with pytest.raises(ValidationError):
            ResearchTutorExchange(
                action="discuss",
                request="",
                answer=answer,
                model_call_id=extra.get("model_call_id"),
                reference=reference_research.VERSION,
                calculation=extra.get("calculation"),
            )


@pytest.mark.parametrize("action", ["discuss", "draft"])
@pytest.mark.parametrize("language", ["en", "de"])
async def test_actual_api_reuses_reference_and_preserves_source_and_history(
    client, db, fake_local, monkeypatch, action, language
):
    from app.db.models import LearnerProfile
    from app.kernel import preferences
    from tests.test_research_tutor import create

    monkeypatch.setattr("tests.test_research_tutor.PASSAGE", SOURCE)
    await registry.seed_defaults(db, installed_ollama_tags={"gemma3:12b"})
    draft = await create(client, prompt=QUERY, tutor_request="")
    learner = (await db.scalars(select(LearnerProfile))).first()
    await preferences.set_pref(db, learner.id, "tutor.response_language", language)
    url = f"/api/knowledge-material/drafts/{draft['id']}/research-tutor"
    response = await client.post(
        url, json={"expected_version": draft["version"], "question_id": "q1", "action": action}
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    exchange = saved["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"][0]
    assert exchange["model_call_id"] is None and exchange["reference"] == reference_research.VERSION
    assert exchange["answer"]["source_quotes"] == [SOURCE, reference_research.REFERENCE]
    assert exchange["answer"]["section" if action == "draft" else "discussion"].startswith(
        "Nein." if language == "de" else "No."
    )
    again = await client.post(
        url, json={"expected_version": saved["version"], "question_id": "q1", "action": action}
    )
    assert again.status_code == 200 and again.json()["version"] == saved["version"]
    assert (
        not fake_local.calls and await db.scalar(select(func.count()).select_from(ModelCall)) == 0
    )


def test_unchanged_language_follows_an_explicit_german_reference_question():
    q = ResearchQuestion(
        id="de",
        prompt="Bedeutet Unveränderlichkeit ein neues Objekt? Unterscheide == und is.",
        findings="Meine Notiz",
    )
    answer = reference_research.answer(SOURCE, q, TutorPresentation())
    assert answer and answer.discussion.startswith("Nein.")
