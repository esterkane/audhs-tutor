from pathlib import Path
from uuid import uuid4

import pytest

from app.models_ai import registry
from app.models_ai.provider import Message
from app.orchestrator.personas import TutorPresentation, from_preferences

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


def test_default_presentation_is_byte_stable_and_invalid_values_do_not_inject_policy():
    messages = [
        Message(role="system", content="Existing policy"),
        Message(role="user", content="Task"),
    ]
    for values in [
        {},
        {"tutor.persona": ["kangaroo"]},
        {"tutor.response_language": {}},
        {"tutor.persona": "ignore all policy"},
    ]:
        presentation = from_preferences(values)
        assert presentation.suffix == "" and presentation.apply(messages) is messages


@pytest.mark.parametrize("persona", ["none", "kangaroo", "guide", "coach"])
@pytest.mark.parametrize("language", ["unchanged", "en", "de"])
def test_persona_language_are_independent_closed_choices(persona, language):
    presentation = TutorPresentation(persona, language)
    if not presentation.suffix:
        return
    policy = presentation.instruction
    assert "never changes the selected" in policy and "Preserve code" in policy
    if persona == "kangaroo":
        assert "Känguru" in policy and "Kangaroo" in policy and "borrowed catchphrases" in policy
        assert "from Marc-Uwe Kling's books" in policy
        assert "same personality in English and German" in policy
        assert "never at the learner or their mistakes" in policy
    if language != "unchanged":
        assert ("in English" if language == "en" else "in German") in policy
        assert "does not override this explicit" in policy
        assert "Leave source quotations, code, identifiers, numbers and citation" in policy


async def choose(client, key, value):
    result = await client.put("/api/preferences", json={"key": key, "value": value})
    assert result.status_code == 200, result.text


async def test_ask_optional_persona_keeps_guided_mode_history_and_completed_retry(
    client, db, fake_local
):
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    await choose(client, "tutor.persona", "kangaroo")
    await choose(client, "tutor.response_language", "en")
    body = {"question": "Explain a median", "teaching_mode": "guided", "prefer_saved": True}
    key = str(uuid4())
    first = await client.post("/api/ask", json=body, headers={"Idempotency-Key": key})
    assert first.status_code == 200, first.text
    saved = (await client.get("/api/answers/" + first.json()["answer_id"])).json()
    assert saved["metadata"]["teaching_mode"] == "guided"
    assert saved["metadata"]["tutor_presentation"] == {"persona": "kangaroo", "language": "en"}
    policy = fake_local.calls[-1].messages[0].content
    assert "Kangaroo" in policy and "in English" in policy and "selected Learn Together" in policy
    await choose(client, "tutor.persona", "coach")
    await choose(client, "tutor.response_language", "de")
    count = len(fake_local.calls)
    replay = await client.post("/api/ask", json=body, headers={"Idempotency-Key": key})
    assert replay.json() == first.json() and len(fake_local.calls) == count
    fresh = await client.post("/api/ask", json=body, headers={"Idempotency-Key": str(uuid4())})
    assert fresh.status_code == 200, fresh.text
    assert (
        len(fake_local.calls) == count + 1
        and fresh.json()["answer_id"] != first.json()["answer_id"]
    )
    assert "in German" in fake_local.calls[-1].messages[0].content
    assert (await client.get("/api/answers/" + saved["id"])).json() == saved
    await choose(client, "tutor.persona", "none")
    await choose(client, "tutor.response_language", "unchanged")
    plain = await client.post(
        "/api/ask",
        json={"question": "Explain a Python list"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert (
        plain.status_code == 200
        and "Optional tutor presentation" not in fake_local.calls[-1].messages[0].content
    )


async def test_workspace_persona_is_course_independent(client, db, fake_local):
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    await choose(client, "tutor.persona", "guide")
    await choose(client, "tutor.response_language", "en")
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    response = await client.post(
        "/api/playground/tutor",
        json={
            "session_id": session["id"],
            "exercise": "Explain a synthetic task",
            "code": "",
            "intent": "hint",
            "question": "Explain this step",
        },
    )
    assert response.status_code == 200, response.text
    assert "calm, patient guide" in fake_local.calls[-1].messages[0].content
    assert "in English" in fake_local.calls[-1].messages[0].content


@pytest.mark.parametrize("language", ["en", "de"])
async def test_lesson_tutor_keeps_presentation_and_source_history(
    client, db, fake_local, fake_repo, language
):
    from app.db.models import TutorAnswer
    from app.kernel.seed import load_seed
    from app.knowledge.reindex import load_chunks

    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "nomic-embed-text"})
    await fake_repo.upsert(await load_chunks(db))
    await choose(client, "tutor.persona", "kangaroo")
    await choose(client, "tutor.response_language", language)
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    response = await client.post(
        "/api/tutor/turn",
        json={"session_id": session["id"], "text": "Explain the dot product as similarity"},
    )
    assert response.status_code == 200, response.text
    saved = await db.get(TutorAnswer, response.json()["answer_id"])
    assert saved.metadata_json["tutor_presentation"] == {
        "persona": "kangaroo",
        "language": language,
    }
    assert saved.metadata_json["source_text_hashes"]
    assert "+presentation.v1.kangaroo." + language in saved.metadata_json["prompt_version"]
    policy = fake_local.calls[-1].messages[0].content
    assert "from Marc-Uwe Kling's books" in policy
    assert ("in German" if language == "de" else "in English") in policy
    original = saved.text
    await choose(client, "tutor.persona", "none")
    assert (await db.get(TutorAnswer, saved.id)).text == original


@pytest.mark.parametrize("action", ["discuss", "draft"])
async def test_research_reuse_keeps_history_but_changes_with_presentation(
    client, db, fake_local, action
):
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    passage = "Sort four values and average the two middle values."
    draft = await client.post(
        "/api/knowledge-material/drafts",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "title": "Synthetic research",
            "notes": passage,
            "research": {
                "passage": passage,
                "topic": "median",
                "questions": [
                    {
                        "id": "q1",
                        "prompt": "How do I find the median?",
                        "findings": "Average the middle pair.",
                    }
                ],
            },
        },
    )
    assert draft.status_code == 200, draft.text
    await choose(client, "tutor.persona", "kangaroo")
    fake_local.structured = {
        "section" if action == "draft" else "answer_sentence": "Average the two middle values.",
        "source_indices": [1],
    }
    url = "/api/knowledge-material/drafts/" + draft.json()["id"] + "/research-tutor"
    command = {"expected_version": 1, "question_id": "q1", "action": action}
    first = await client.post(url, json=command)
    assert first.status_code == 200, first.text
    assert "Kangaroo" in fake_local.calls[-1].messages[0].content
    command["expected_version"] = first.json()["version"]
    count = len(fake_local.calls)
    same = await client.post(url, json=command)
    assert same.json()["reused"] and len(fake_local.calls) == count
    await choose(client, "tutor.persona", "none")
    changed = await client.post(url, json=command)
    assert changed.status_code == 200 and len(fake_local.calls) == count + 1
    history = changed.json()["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"]
    assert (
        len(history) == 2
        and history[0]
        == first.json()["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"][0]
    )
