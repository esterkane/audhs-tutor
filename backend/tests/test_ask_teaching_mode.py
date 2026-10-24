"""Explicit teaching choices survive branches without becoming learning evidence."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db.models import TutorAnswer
from app.models_ai import registry
from app.schemas.ask import AskQuestion


def test_legacy_request_and_explicit_choice():
    for mode in (None,):
        assert (
            "teaching_mode" not in AskQuestion(question="Explain", teaching_mode=mode).model_dump()
        )
    assert (
        AskQuestion(question="Explain", teaching_mode="guided").model_dump()["teaching_mode"]
        == "guided"
    )
    with pytest.raises(ValidationError):
        AskQuestion(question="Explain", teaching_mode="automatic")


async def test_mode_inheritance_branches_override_and_frozen_retry(client, db, fake_local):
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})

    async def ask(body, key=None):
        response = await client.post(
            "/api/ask", json=body, headers={"Idempotency-Key": key or str(uuid4())}
        )
        assert response.status_code == 200, response.text
        saved = (await client.get(f"/api/answers/{response.json()['answer_id']}")).json()
        return response.json(), saved

    root, _ = await ask({"question": "Explain fitting", "teaching_mode": "guided"})
    parent = root["answer_id"]
    for index in range(4):
        result, saved = await ask({"question": f"Explain step {index}", "parent_answer_id": parent})
        assert saved["metadata"]["teaching_mode"] == "guided"
        assert "explicitly selected Learn Together" in fake_local.calls[-1].messages[0].content
        parent = result["answer_id"]
    _, saved = await ask(
        {"question": "Explain directly", "parent_answer_id": parent, "teaching_mode": "explicit"}
    )
    assert saved["metadata"]["teaching_mode"] == "explicit"
    assert "explicitly selected Learn Together" not in fake_local.calls[-1].messages[0].content
    key = str(uuid4())
    body = {"question": "Another branch", "parent_answer_id": root["answer_id"]}
    sibling, saved = await ask(body, key)
    assert saved["metadata"]["teaching_mode"] == "guided"
    _, saved = await ask({"question": "New topic"})
    assert saved["metadata"]["teaching_mode"] == "explicit"
    conflict = await client.post(
        "/api/ask", json={**body, "teaching_mode": "explicit"}, headers={"Idempotency-Key": key}
    )
    assert conflict.status_code == 409
    await db.delete(await db.get(TutorAnswer, root["answer_id"]))
    await db.commit()
    count = len(fake_local.calls)
    replay, _ = await ask(body, key)
    assert replay == sibling
    assert len(fake_local.calls) == count


@pytest.mark.parametrize("mode", [None, "invalid", {}, ["guided"]])
async def test_invalid_historical_mode_defaults_to_explicit(client, db, fake_local, mode):
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    response = await client.post(
        "/api/ask", json={"question": "Explain fitting"}, headers={"Idempotency-Key": str(uuid4())}
    )
    parent = await db.get(TutorAnswer, response.json()["answer_id"])
    parent.metadata_json = {**parent.metadata_json, "teaching_mode": mode}
    await db.commit()
    response = await client.post(
        "/api/ask",
        json={"question": "Continue", "parent_answer_id": parent.id},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    saved = (await client.get(f"/api/answers/{response.json()['answer_id']}")).json()
    assert saved["metadata"]["teaching_mode"] == "explicit"
