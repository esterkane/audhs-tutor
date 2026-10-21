import json

import httpx
import pytest

from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import Message, ModelSpec, StructuredOutputError
from app.schemas.knowledge_authoring import ResearchDiscussion


@pytest.mark.parametrize("invalid", [False, True])
async def test_native_schema_preserves_instructions_capacity_defaults_and_validation(
    monkeypatch, invalid
):
    posts = []

    async def handle(request):
        body = json.loads(request.content)
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "local"}})
        posts.append(body)
        return httpx.Response(
            200,
            json={
                "model": "installed-local",
                "done": True,
                "done_reason": "stop",
                "message": {
                    "role": "assistant",
                    "thinking": "private reasoning",
                    "content": json.dumps(
                        {
                            "answer_sentence": "" if invalid else "The median is 6.",
                            "source_indices": [1],
                        }
                    ),
                },
                "prompt_eval_count": 111,
                "eval_count": 42,
            },
        )

    original = httpx.AsyncClient

    def mocked_client(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handle)
        return original(**kwargs)

    monkeypatch.setattr("httpx.AsyncClient", mocked_client)
    provider = OllamaProvider("http://localhost:11434", context_tokens=16384, keep_alive_s=300)
    spec = ModelSpec(
        registry_id="local", provider="ollama", model="installed-local", context_len=32768
    )
    messages = [
        Message(role="system", content="Use the source and correct the finding."),
        Message(role="user", content="Exact source: average 4 and 8. Finding: choose 4."),
    ]
    if invalid:
        with pytest.raises(StructuredOutputError):
            await provider.complete(
                spec,
                messages,
                response_model=ResearchDiscussion,
                max_tokens=1800,
                metadata={"structured_output": "native_schema"},
            )
        assert len(posts) == 1  # Gateway, never Instructor, owns logged repairs.
    else:
        legacy = await provider.complete(
            spec, messages, response_model=ResearchDiscussion, max_tokens=1800
        )
        native = await provider.complete(
            spec,
            messages,
            response_model=ResearchDiscussion,
            max_tokens=1800,
            metadata={"structured_output": "native_schema"},
        )
        assert posts[0]["messages"] == posts[1]["messages"]
        assert posts[0]["format"] == "json"
        assert posts[1]["format"] == ResearchDiscussion.model_json_schema()
        for body in posts:
            assert body["options"]["num_ctx"] == 16384
            assert body["options"]["num_predict"] == 1800
            assert body["options"]["temperature"] == 0.2
            assert body.get("think") is not False
        assert legacy.parsed.model_dump() == native.parsed.model_dump()
        assert native.tokens_in == 111 and native.tokens_out == 42
        assert native.raw["reasoning_chars"] == len("private reasoning")
        assert "private reasoning" not in native.model_dump_json()


async def test_native_research_validation_repair_is_logged_by_gateway(client, db, monkeypatch):
    from uuid import uuid4

    from sqlalchemy import select

    from app.db.models import ModelCall
    from app.models_ai.registry import seed_defaults

    await seed_defaults(db, installed_ollama_tags={"gemma3:12b", "llama3.1:8b"})
    chats = []

    async def handle(request):
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "local"}})
        chats.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "local",
                "done": True,
                "done_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "answer_sentence": ""
                            if len(chats) == 1
                            else "Average the two middle values.",
                            "source_indices": [1],
                        }
                    ),
                },
                "prompt_eval_count": 100,
                "eval_count": 30,
            },
        )

    original = httpx.AsyncClient

    def mocked_client(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handle)
        return original(**kwargs)

    monkeypatch.setattr("httpx.AsyncClient", mocked_client)
    client._transport.app.state.providers["ollama"] = OllamaProvider("http://localhost:11434")
    passage = "For even-sized data, average the two middle sorted values."
    draft = (
        await client.post(
            "/api/knowledge-material/drafts",
            headers={"Idempotency-Key": str(uuid4())},
            json={
                "title": "Logged native repair",
                "notes": passage,
                "research": {
                    "passage": passage,
                    "topic": "median",
                    "questions": [
                        {"id": "q1", "prompt": "How?", "findings": "Choose the lower middle."}
                    ],
                },
            },
        )
    ).json()
    response = await client.post(
        f"/api/knowledge-material/drafts/{draft['id']}/research-tutor",
        json={"expected_version": 1, "question_id": "q1", "action": "discuss"},
    )
    assert response.status_code == 200, response.text
    assert len(chats) == 2
    rows = (await db.scalars(select(ModelCall).order_by(ModelCall.attempt))).all()
    assert len(rows) == 2 and [row.attempt for row in rows] == [1, 2]
    assert not rows[0].ok and rows[1].ok
    assert all(row.metadata_json["structured_output"] == "native_schema" for row in rows)
    exchanges = response.json()["payload"]["authoring"]["research"]["questions"][0][
        "tutor_exchanges"
    ]
    assert len(exchanges) == 1 and exchanges[0]["model_call_id"] == rows[1].id
