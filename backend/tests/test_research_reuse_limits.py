import pytest
from sqlalchemy import func, select

from app.db.models import ModelCall
from app.models_ai import registry
from app.orchestrator import research_tutor
from tests.test_research_tutor import create


@pytest.mark.parametrize("kind", ["checked", "model"])
@pytest.mark.parametrize("action", ["discuss", "draft"])
async def test_exact_reuse_at_capacity_preserves_all_history_and_rejects_new_answers(
    client, db, fake_local, monkeypatch, kind, action
):
    import tests.test_research_tutor as fixtures

    await registry.seed_defaults(db, installed_ollama_tags={"gemma3:12b", "llama3.1:8b"})
    if kind == "checked":
        monkeypatch.setattr(fixtures, "PASSAGE", "Python 3:\nvalue = 3\n")
    legacy = [
        {
            "action": "discuss",
            "request": f"Earlier {i}",
            "model_call_id": f"old-{i}",
            "answer": {"discussion": f"Earlier saved reply {i}"},
        }
        for i in range(11)
    ]
    draft = await create(
        client,
        prompt="What does `value + 1` return?" if kind == "checked" else "How is the median found?",
        tutor_request="",
        tutor_exchanges=legacy,
    )
    fake_local.structured = {
        "section" if action == "draft" else "answer_sentence": "Average the two middle values.",
        "source_indices": [1],
    }
    url = f"/api/knowledge-material/drafts/{draft['id']}/research-tutor"
    command = {"expected_version": 1, "question_id": "q1", "action": action}
    first = await client.post(url, json=command)
    assert first.status_code == 200, first.text
    saved = first.json()
    history = saved["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"]
    assert len(history) == 12
    assert [x["answer"]["discussion"] for x in history[:11]] == [
        x["answer"]["discussion"] for x in legacy
    ]
    command["expected_version"] = saved["version"]
    repeated = await client.post(url, json=command)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["reused"] and repeated.json()["version"] == saved["version"]
    assert repeated.json()["payload"] == saved["payload"]
    fresh = await client.post(
        url, json={**command, "action": "draft" if action == "discuss" else "discuss"}
    )
    assert fresh.status_code == 422 and fresh.json()["error"]["code"] == "research_history_full"
    if kind == "model":
        refreshed = await client.post(url, json={**command, "refresh": True})
        assert refreshed.status_code == 422
        assert refreshed.json()["error"]["code"] == "research_history_full"
    monkeypatch.setattr(research_tutor, "_REUSE_KEY", b"changed-key" * 3)
    invalid = await client.post(url, json=command)
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "research_history_full"
    assert len(fake_local.calls) == (0 if kind == "checked" else 1)
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == (
        0 if kind == "checked" else 1
    )
    resumed = (await client.get(f"/api/curriculum/drafts/{draft['id']}")).json()
    assert resumed["payload"] == saved["payload"]


async def test_checked_answer_does_not_require_encoding_findings_as_model_context(
    client, fake_local, monkeypatch
):
    import tests.test_research_tutor as fixtures

    monkeypatch.setattr(fixtures, "PASSAGE", "Python 3:\nvalue = 3\n")
    history = [
        {
            "action": "discuss",
            "request": "Earlier",
            "model_call_id": f"old-{i}",
            "answer": {"discussion": "x" * 2000},
        }
        for i in range(2)
    ]
    draft = await create(
        client,
        prompt="What does `value + 1` return?",
        tutor_request="",
        findings="f" * 8000,
        evidence="e" * 8000,
        section="s" * 4000,
        tutor_exchanges=history,
    )
    response = await client.post(
        f"/api/knowledge-material/drafts/{draft['id']}/research-tutor",
        json={"expected_version": 1, "question_id": "q1", "action": "discuss"},
    )
    assert response.status_code == 200, response.text
    q = response.json()["payload"]["authoring"]["research"]["questions"][0]
    assert q["findings"] == "f" * 8000 and q["evidence"] == "e" * 8000
    assert len(q["tutor_exchanges"]) == 3 and not fake_local.calls
