import pytest
from sqlalchemy import func, select

from app.db.models import AssessmentAttempt, CompetencyEvidence, ModelCall
from app.orchestrator.literal_research import answer
from app.orchestrator.personas import TutorPresentation
from app.schemas.knowledge_authoring import ResearchQuestion
from tests.test_research_tutor import create

SOURCE = "Python 3:\nlabel = 'Tag '\n"
QUESTION = "What do `label + 4`, `4 + 2.5` and `[1] + ['x']` return?"


@pytest.mark.parametrize("language", ["en", "de", "unchanged"])
def test_complete_results_are_language_scoped_and_source_preserving(language):
    result = answer(
        SOURCE, ResearchQuestion(id="q", prompt=QUESTION), TutorPresentation("kangaroo", language)
    )
    assert result is not None
    assert all(
        value in result.discussion for value in ["TypeError", "str + int", "6.5", "[1, 'x']"]
    )
    assert ("ergibt" if language == "de" else "evaluates to") in result.discussion
    assert result.source_quotes == [SOURCE] and not result.next_question


@pytest.mark.parametrize(
    "changes",
    [
        {"tutor_request": "Explain why"},
        {"unresolved": "What about subclasses?"},
        {"memory_ids": ["a" * 64]},
    ],
)
def test_broader_requests_keep_model_context(changes):
    question = ResearchQuestion(id="q", prompt=QUESTION).model_copy(update=changes)
    assert answer(SOURCE, question, TutorPresentation()) is None


@pytest.mark.parametrize("action", ["discuss", "draft"])
@pytest.mark.parametrize("hosted", [False, True])
async def test_api_calculation_reuse_preserves_history_without_inference(
    client, db, fake_local, monkeypatch, action, hosted
):
    import tests.test_research_tutor as fixtures

    monkeypatch.setattr(fixtures, "PASSAGE", SOURCE)
    setting = await client.put(
        "/api/preferences", json={"key": "authoring.enabled", "value": hosted}
    )
    assert setting.status_code == 200
    legacy = {
        "action": "discuss",
        "request": "Earlier request",
        "model_call_id": "earlier-model",
        "answer": {"discussion": "Earlier research reply.", "source_quotes": [SOURCE]},
    }
    draft = await create(client, prompt=QUESTION, tutor_request="", tutor_exchanges=[legacy])
    url = f"/api/knowledge-material/drafts/{draft['id']}/research-tutor"
    response = await client.post(
        url, json={"expected_version": 1, "question_id": "q1", "action": action}
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    history = saved["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"]
    assert len(history) == 2 and history[0]["answer"]["discussion"] == "Earlier research reply."
    exchange = history[-1]
    assert exchange["calculation"] == "python.literal-expression.v1"
    assert (
        exchange["model_call_id"] is None
        and "6.5" in exchange["answer"]["section" if action == "draft" else "discussion"]
    )
    again = await client.post(
        url, json={"expected_version": saved["version"], "question_id": "q1", "action": action}
    )
    assert again.status_code == 200 and again.json()["reused"]
    resumed = (await client.get(f"/api/curriculum/drafts/{draft['id']}")).json()
    assert resumed["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"] == history
    assert (
        not fake_local.calls and await db.scalar(select(func.count()).select_from(ModelCall)) == 0
    )
    assert await db.scalar(select(func.count()).select_from(AssessmentAttempt)) == 0
    assert await db.scalar(select(func.count()).select_from(CompetencyEvidence)) == 0


async def test_api_broader_request_retains_normal_model_path(client, db, fake_local, monkeypatch):
    import tests.test_research_tutor as fixtures
    from app.models_ai import registry

    await registry.seed_defaults(db, installed_ollama_tags={"gemma3:12b", "llama3.1:8b"})
    monkeypatch.setattr(fixtures, "PASSAGE", SOURCE)
    draft = await create(
        client, prompt=QUESTION, tutor_request="Explain the operator requirements."
    )
    fake_local.structured = {
        "answer_sentence": "The operation depends on its concrete operands.",
        "source_indices": [1],
    }
    response = await client.post(
        f"/api/knowledge-material/drafts/{draft['id']}/research-tutor",
        json={"expected_version": 1, "question_id": "q1", "action": "discuss"},
    )
    assert response.status_code == 200, response.text
    exchange = response.json()["payload"]["authoring"]["research"]["questions"][0][
        "tutor_exchanges"
    ][0]
    assert exchange["model_call_id"] and not exchange.get("calculation")
    assert len(fake_local.calls) == 1
