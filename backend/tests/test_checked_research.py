from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.db.models import AssessmentAttempt, CompetencyEvidence, ModelCall
from app.orchestrator.checked_research import answer
from app.orchestrator.personas import TutorPresentation
from app.schemas.knowledge_authoring import (
    ResearchQuestion,
    ResearchTutorAnswer,
    ResearchTutorExchange,
)

SOURCE = (
    "In Python, text = 'go'. text * -3 returns ''. text * 0 returns ''. text * 2 returns 'gogo'."
)
QUESTION = "What do text * -3, text * 0 and text * 2 return, and does text change?"
GERMAN = "Was geben text * -3, text * 0 und text * 2 zurück, und ändert sich text?"


@pytest.mark.parametrize("language", ["en", "de", "unchanged"])
@pytest.mark.parametrize("prompt", [QUESTION, GERMAN])
def test_checked_answer_covers_every_result_without_invented_mechanisms(language, prompt):
    result = answer(
        SOURCE, ResearchQuestion(id="q", prompt=prompt), TutorPresentation("kangaroo", language)
    )
    assert result is not None
    for code in ["text * -3 = ''", "text * 0 = ''", "text * 2 = 'gogo'"]:
        assert code in result.discussion
    german = language == "de" or (language == "unchanged" and prompt == GERMAN)
    assert ("unverändert" if german else "unchanged") in result.discussion
    assert result.discussion.count("unverändert" if german else "unchanged") == 1
    assert "object" not in result.discussion and "Objekt" not in result.discussion
    assert result.source_quotes == [SOURCE] and not result.next_question


@pytest.mark.parametrize(
    "change",
    [
        {"tutor_request": "Explain complexity instead"},
        {"unresolved": "What about subclasses?"},
        {"memory_ids": ["a" * 64]},
        {"prompt": QUESTION + " Why did I make this mistake?"},
    ],
)
def test_broader_help_and_selected_memories_defer_instead_of_losing_context(change):
    question = ResearchQuestion(id="q", prompt=QUESTION).model_copy(update=change)
    assert answer(SOURCE, question, TutorPresentation()) is None
    assert (
        answer(
            SOURCE + " text += 'other'",
            ResearchQuestion(id="q", prompt=QUESTION),
            TutorPresentation(),
        )
        is None
    )


def test_source_claim_is_not_used_as_calculation_truth_and_legacy_history_is_stable():
    wrong = SOURCE.replace("returns 'gogo'", "returns 'incorrect'")
    result = answer(wrong, ResearchQuestion(id="q", prompt=QUESTION), TutorPresentation())
    assert result is not None and "text * 2 = 'gogo'" in result.discussion
    assert result.source_quotes == [wrong]
    legacy = dict(
        action="discuss",
        request="",
        answer=ResearchTutorAnswer().model_dump(),
        model_call_id="old",
        memories=[],
        cache_token=None,
    )
    assert ResearchTutorExchange.model_validate(legacy).model_dump() == legacy
    with pytest.raises(ValidationError):
        ResearchTutorExchange.model_validate({**legacy, "model_call_id": None})
    with pytest.raises(ValidationError):
        ResearchTutorExchange.model_validate(
            {**legacy, "calculation": "python.string-repetition.v1"}
        )


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("action", ["discuss", "draft"])
async def test_checked_flow_needs_no_model_preserves_history_and_reuse(
    client, db, fake_local, language, action
):
    # No model registry is seeded: a complete local calculation needs no ready LLM.
    for key, value in [("tutor.persona", "kangaroo"), ("tutor.response_language", language)]:
        assert (
            await client.put("/api/preferences", json={"key": key, "value": value})
        ).status_code == 200
    prior = ResearchTutorExchange(
        action="discuss",
        request="Earlier help",
        answer=ResearchTutorAnswer(discussion="Earlier saved wording."),
        model_call_id="historic-model-call",
    )
    draft = await client.post(
        "/api/knowledge-material/drafts",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "title": "Synthetic checked research",
            "notes": SOURCE,
            "research": {
                "passage": SOURCE,
                "topic": "Python",
                "questions": [
                    {
                        "id": "q",
                        "prompt": QUESTION,
                        "findings": "I thought the negative count raises ValueError.",
                        "tutor_exchanges": [prior.model_dump()],
                    }
                ],
            },
        },
    )
    assert draft.status_code == 200, draft.text
    url = "/api/knowledge-material/drafts/" + draft.json()["id"] + "/research-tutor"
    body = {"expected_version": draft.json()["version"], "question_id": "q", "action": action}
    response = await client.post(url, json=body)
    assert response.status_code == 200, response.text
    saved = response.json()
    history = saved["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"]
    assert len(history) == 2 and history[0] == prior.model_dump()
    assert (
        history[-1]["model_call_id"] is None
        and history[-1]["calculation"] == "python.string-repetition.v1"
    )
    assert not fake_local.calls
    for table in [ModelCall, AssessmentAttempt, CompetencyEvidence]:
        assert await db.scalar(select(func.count()).select_from(table)) == 0
    body["expected_version"] = saved["version"]
    replay = await client.post(url, json={**body, "refresh": True})
    assert replay.status_code == 200 and replay.json()["reused"]
    assert replay.json()["payload"] == saved["payload"]
    # A changed language must not reuse or rewrite the earlier saved reply.
    await client.put(
        "/api/preferences",
        json={"key": "tutor.response_language", "value": "de" if language == "en" else "en"},
    )
    changed = await client.post(url, json=body)
    assert changed.status_code == 200 and not changed.json()["reused"]
    history2 = changed.json()["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"]
    assert history2[:2] == history and len(history2) == 3
