import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.db.models import ModelCall
from app.models_ai.budget import Budget
from app.models_ai.gateway import ModelGateway
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import InferenceTiming, Message, ModelSpec, TaskClass
from app.models_ai.registry import seed_defaults
from app.models_ai.routing import Router
from app.schemas.knowledge_authoring import ResearchDiscussion


@pytest.mark.parametrize("diagnostics", ["valid", "absent", "bool", "negative", "huge"])
async def test_native_timing_is_optional_numeric_and_does_not_change_answer(
    monkeypatch, diagnostics
):
    async def handle(request):
        body = {
            "done": True,
            "done_reason": "stop",
            "model": "local",
            "message": {
                "role": "assistant",
                "thinking": "private reasoning",
                "content": json.dumps(
                    {"answer_sentence": "The median is 6.", "source_indices": [1]}
                ),
            },
        }
        if diagnostics != "absent":
            body.update(
                load_duration=1_000_000,
                prompt_eval_duration=2_000_000,
                eval_duration=3_000_000,
                total_duration=7_000_000,
                prompt_eval_count=10,
                eval_count=20,
            )
            if diagnostics == "bool":
                body["eval_count"] = True
            if diagnostics == "negative":
                body["eval_duration"] = -1
            if diagnostics == "huge":
                body["eval_count"] = 10**30
        return httpx.Response(200, json=body)

    original = httpx.AsyncClient

    def client(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handle)
        return original(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    monkeypatch.setattr(OllamaProvider, "validate_local_transport", AsyncMock())
    result = await OllamaProvider("http://localhost:11434").complete(
        ModelSpec(registry_id="local", provider="ollama", model="local"),
        [Message(role="user", content="Average 4 and 8.")],
        response_model=ResearchDiscussion,
        metadata={"structured_output": "native_schema"},
    )
    assert result.parsed.answer_sentence == "The median is 6."
    assert "private reasoning" not in result.model_dump_json()
    assert "inference_timing" not in result.model_dump()
    if diagnostics == "valid":
        assert result.inference_timing.model_dump() == {
            "load_ms": 1.0,
            "prompt_ms": 2.0,
            "generation_ms": 3.0,
            "total_ms": 7.0,
            "prompt_tokens": 10,
            "generated_tokens": 20,
        }
    else:
        assert result.inference_timing is None


async def test_gateway_persists_only_typed_content_free_timings(db, settings, fake_local):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    complete = fake_local.complete

    async def measured(*args, **kwargs):
        result = await complete(*args, **kwargs)
        result.inference_timing = InferenceTiming(
            load_ms=1,
            prompt_ms=2,
            generation_ms=3,
            total_ms=7,
            prompt_tokens=10,
            generated_tokens=20,
        )
        result.raw = {"private_reasoning": "must not persist", "learner_text": "private"}
        return result

    fake_local.complete = measured
    gateway = ModelGateway(db, Router(settings.routing_profile), {"ollama": fake_local}, Budget(0))
    output = await gateway.complete(
        TaskClass.EXPLAIN_SIMPLE, [Message(role="user", content="Explain.")]
    )
    row = await db.get(ModelCall, output.model_call_id)
    assert row.metadata_json["inference_timing"] == output.result.inference_timing.model_dump()
    assert "private" not in json.dumps(row.metadata_json)
