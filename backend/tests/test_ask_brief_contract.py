"""Retained learner context is bounded data, separate from source evidence."""

import pytest
from pydantic import ValidationError

from app.schemas.ask import AskQuestion, ConversationBrief


def test_absent_brief_preserves_legacy_request_shape():
    value = AskQuestion(question="Explain parameters")
    assert "conversation_brief" not in value.model_dump(mode="json")
    assert value.model_dump(mode="json") == {
        "question": "Explain parameters",
        "area_id": None,
        "parent_answer_id": None,
    }


def test_explicit_empty_brief_survives_serialization_for_clear():
    value = AskQuestion(question="Start over", conversation_brief=ConversationBrief())
    assert value.model_dump(mode="json")["conversation_brief"] == {
        "version": 1,
        "task": "",
        "notes": "",
        "examples": "",
        "unresolved": "",
    }


@pytest.mark.parametrize(
    "field,limit", [("task", 500), ("notes", 1500), ("examples", 1000), ("unresolved", 500)]
)
def test_brief_field_limits(field, limit):
    assert getattr(ConversationBrief(**{field: "x" * limit}), field) == "x" * limit
    with pytest.raises(ValidationError):
        ConversationBrief(**{field: "x" * (limit + 1)})


@pytest.mark.parametrize(
    "extra", [{"verified": True}, {"version": 2}, {"source_ids": ["invented"]}]
)
def test_brief_cannot_claim_verification_or_source_links(extra):
    with pytest.raises(ValidationError):
        ConversationBrief(**extra)


async def test_effective_brief_inherits_and_clear_does_not_resurrect(client, db, fake_local):
    from uuid import uuid4

    from app.models_ai import registry

    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    parent = None
    for index in range(6):
        body = {"question": f"Explain step {index}", "parent_answer_id": parent}
        if index == 1:
            body["conversation_brief"] = {
                "task": "Understand training weights",
                "examples": "Imaginary salary 80000",
            }
        if index == 4:
            body["conversation_brief"] = {}
        response = await client.post(
            "/api/ask", json=body, headers={"Idempotency-Key": str(uuid4())}
        )
        assert response.status_code == 200, response.text
        parent = response.json()["answer_id"]
        saved = (await client.get(f"/api/answers/{parent}")).json()
        context = saved["metadata"]["conversation_brief"]
        blocks = [
            m.content
            for m in fake_local.calls[-1].messages
            if m.content.startswith("<conversation_brief>")
        ]
        if 1 <= index <= 3:
            assert context["origin"] == "learner_supplied_unverified"
            assert len(blocks) == 1 and "Imaginary salary 80000" in blocks[0]
        else:
            assert blocks == []
        if index >= 4:
            assert context["mode"] == "cleared"


@pytest.mark.parametrize(
    "raw",
    [
        {"mode": [], "value": None},
        {"mode": {}, "value": None},
        {"mode": [], "value": {}},
        {"mode": {}, "value": {}},
        {"value": {}},
        {
            "mode": "supplied",
            "origin": "learner_supplied_unverified",
            "value": {"task": "unverified"},
        },
        {
            "mode": "supplied",
            "origin": "learner_supplied_unverified",
            "value": ConversationBrief(task="changed").model_dump(),
            "hash": "wrong",
        },
    ],
)
def test_malformed_stored_brief_is_unavailable(raw):
    from app.db.models import TutorAnswer
    from app.orchestrator.ask_brief import resolve

    parent = TutorAnswer(id="parent", metadata_json={"conversation_brief": raw})
    assert resolve(None, parent) == {"mode": "unavailable", "value": None}


def test_null_keeps_legacy_inheritance_semantics():
    assert (
        "conversation_brief"
        not in AskQuestion(question="Continue", conversation_brief=None).model_dump()
    )


async def test_followup_survives_malformed_saved_context_mode(client, db, fake_local):
    from uuid import uuid4

    from app.db.models import TutorAnswer
    from app.models_ai import registry

    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    root = await client.post(
        "/api/ask",
        json={"question": "Explain training"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert root.status_code == 200, root.text
    parent_id = root.json()["answer_id"]
    parent = await db.get(TutorAnswer, parent_id)
    parent.metadata_json = {
        **parent.metadata_json,
        "conversation_brief": {"mode": [], "value": {"task": "CORRUPT_CONTEXT"}},
    }
    await db.commit()
    response = await client.post(
        "/api/ask",
        json={"question": "Explain the next step", "parent_answer_id": parent_id},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    saved = (await client.get(f"/api/answers/{response.json()['answer_id']}")).json()
    assert saved["metadata"]["conversation_brief"] == {"mode": "unavailable", "value": None}
    assert all("CORRUPT_CONTEXT" not in message.content for message in fake_local.calls[-1].messages)


async def test_brief_branch_identity_and_exact_replay(client, db, fake_local):
    from uuid import uuid4

    from app.db.models import TutorAnswer
    from app.models_ai import registry

    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})

    async def ask(body, key=None):
        response = await client.post(
            "/api/ask", json=body, headers={"Idempotency-Key": key or str(uuid4())}
        )
        assert response.status_code == 200, response.text
        return response.json()

    root = await ask(
        {"question": "Explain training", "conversation_brief": {"task": "Original task"}}
    )
    changed = await ask(
        {
            "question": "New direction",
            "parent_answer_id": root["answer_id"],
            "conversation_brief": {"task": "Changed task"},
        }
    )
    key = str(uuid4())
    body = {"question": "Another branch", "parent_answer_id": root["answer_id"]}
    sibling = await ask(body, key)
    saved = (await client.get(f"/api/answers/{sibling['answer_id']}")).json()
    assert saved["metadata"]["conversation_brief"]["value"]["task"] == "Original task"
    assert saved["metadata"]["conversation_brief"]["parent_answer_id"] == root["answer_id"]
    assert changed["answer_id"] != sibling["answer_id"]
    conflict = await client.post(
        "/api/ask", json={**body, "conversation_brief": {}}, headers={"Idempotency-Key": key}
    )
    assert conflict.status_code == 409
    await db.delete(await db.get(TutorAnswer, root["answer_id"]))
    await db.commit()
    count = len(fake_local.calls)
    assert await ask(body, key) == sibling
    assert len(fake_local.calls) == count
