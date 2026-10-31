import json

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import OllamaInferenceOptions, Settings
from app.db.models import ModelCall
from app.kernel.learner import get_or_create_owner
from app.models_ai.benchmark_gateway import BenchmarkRouter
from app.models_ai.budget import Budget
from app.models_ai.factory import build_providers
from app.models_ai.gateway import ModelGateway, StreamHandle
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import Message, ModelSpec, TaskClass
from app.models_ai.registry import seed_defaults
from app.models_ai.source_policy import SourcePolicyDenied
from app.schemas.knowledge_authoring import ResearchDiscussion

SPEC = ModelSpec(
    registry_id="candidate", provider="ollama", model="installed-local", context_len=32768
)
MESSAGES = [Message(role="user", content="Discuss the supplied synthetic source.")]
OPTIONS = OllamaInferenceOptions(reasoning_effort="low", temperature=1.0)


def reply(*, invalid=False, done=True):
    return {
        "model": "installed-local",
        "done": done,
        "done_reason": "stop",
        "message": {
            "role": "assistant",
            "thinking": "private synthetic reasoning",
            "content": json.dumps(
                {"answer_sentence": "" if invalid else "A complete answer.", "source_indices": [1]}
            ),
        },
        "prompt_eval_count": 111,
        "eval_count": 42,
        "load_duration": 1,
        "prompt_eval_duration": 1,
        "eval_duration": 1,
        "total_duration": 3,
    }


def intercept(monkeypatch, *, thinking=None, remote=False, invalid_first=False):
    posts = []
    original = httpx.AsyncClient

    async def handle(request):
        if request.url.path == "/api/show":
            info = {"model_info": {"general.architecture": "local"}, "thinking": thinking}
            if remote:
                info["remote_model"] = "remote-model"
            return httpx.Response(200, json=info)
        body = json.loads(request.content)
        posts.append(body)
        if body.get("stream"):
            first = {
                "model": "installed-local",
                "done": False,
                "message": {"role": "assistant", "content": "Visible answer."},
            }
            last = reply()
            last["message"]["content"] = ""
            return httpx.Response(
                200,
                content=json.dumps(first) + "\n" + json.dumps(last) + "\n",
                headers={"content-type": "application/x-ndjson"},
            )
        return httpx.Response(200, json=reply(invalid=invalid_first and len(posts) == 1))

    def client(**kwargs):
        async def checked_handle(request):
            # The SDK constructs a temporary client that our adapter closes unused.
            # Verify every client that actually sends metadata or inference content.
            assert kwargs.get("trust_env") is False
            assert kwargs.get("follow_redirects") is False
            return await handle(request)

        return original(**{**kwargs, "transport": httpx.MockTransport(checked_handle)})

    monkeypatch.setattr("httpx.AsyncClient", client)
    return posts


def provider():
    return OllamaProvider(
        "http://127.0.0.1:11434",
        context_tokens=16384,
        inference_options={SPEC.registry_id: OPTIONS},
    )


@pytest.mark.parametrize("mode", ["plain", "legacy_json", "native_schema", "stream"])
async def test_explicit_options_reach_every_chat_transport_without_reducing_limits(
    monkeypatch, mode
):
    posts = intercept(
        monkeypatch, thinking={"values": ["low", "medium", "high"], "default": "medium"}
    )
    configured = provider()
    if mode == "stream":
        events = [event async for event in configured.stream(SPEC, MESSAGES, max_tokens=1800)]
        assert "Visible answer." in events
    else:
        result = await configured.complete(
            SPEC,
            MESSAGES,
            max_tokens=1800,
            response_model=ResearchDiscussion if mode != "plain" else None,
            metadata={"structured_output": "native_schema"} if mode == "native_schema" else None,
        )
        assert result.tokens_out == 42
    assert len(posts) == 1
    assert posts[0]["think"] == "low"
    assert posts[0]["options"]["temperature"] == 1.0
    assert posts[0]["options"]["num_ctx"] == 16384
    assert posts[0]["options"]["num_predict"] == 1800


async def test_defaults_and_other_registry_ids_keep_existing_temperature_and_thinking(monkeypatch):
    posts = intercept(monkeypatch)
    configured = provider()
    other = SPEC.model_copy(update={"registry_id": "unchanged"})
    await configured.complete(other, MESSAGES, temperature=0.2, max_tokens=1800)
    assert posts[0]["options"]["temperature"] == 0.2
    assert "think" not in posts[0]
    assert configured.inference_options_for(other) == {}


@pytest.mark.parametrize("thinking", [None, {}, {"values": [True, False]}, {"values": ["high"]}])
async def test_unverified_or_unsupported_named_level_refused_before_content(monkeypatch, thinking):
    posts = intercept(monkeypatch, thinking=thinking)
    with pytest.raises(SourcePolicyDenied, match="thinking level"):
        await provider().complete(SPEC, MESSAGES)
    assert posts == []


async def test_remote_weights_refused_even_with_supported_thinking_level(monkeypatch):
    posts = intercept(monkeypatch, thinking={"values": ["low"]}, remote=True)
    with pytest.raises(SourcePolicyDenied):
        await provider().complete(SPEC, MESSAGES)
    assert posts == []


async def test_speed_probe_uses_the_same_explicit_controls_and_capacity(monkeypatch):
    posts = intercept(monkeypatch, thinking={"values": ["low"]})
    await provider().generate_stats(SPEC, "Synthetic speed probe", max_tokens=200)
    assert posts[0]["think"] == "low"
    assert posts[0]["options"] == {"num_predict": 200, "temperature": 1.0, "num_ctx": 16384}


def test_settings_are_opt_in_typed_and_wired_without_hosted_changes():
    settings = Settings(
        _env_file=None,
        openai_api_key="",
        anthropic_api_key="",
        ollama_inference_options={"candidate": OPTIONS},
    )
    providers = build_providers(settings)
    assert set(providers) == {"ollama"}
    assert isinstance(providers["ollama"], OllamaProvider)
    assert providers["ollama"].inference_options_for(SPEC) == {
        "reasoning_effort": "low",
        "temperature": 1.0,
    }
    assert Settings(_env_file=None).ollama_inference_options == {}


@pytest.mark.parametrize(
    "value",
    [
        {"reasoning_effort": "unknown"},
        {"temperature": -0.1},
        {"temperature": 2.1},
        {"temperature": float("nan")},
        {"temperature": float("inf")},
        {"api_base": "https://example.invalid"},
        {"max_tokens": 20},
        {"num_ctx": 1024},
    ],
)
def test_configuration_cannot_override_transport_or_capacity(value):
    with pytest.raises(ValidationError):
        OllamaInferenceOptions.model_validate(value)


async def test_gateway_records_configured_options_on_each_repair_and_stream(db, monkeypatch):
    posts = intercept(monkeypatch, thinking={"values": ["low"]}, invalid_first=True)
    await seed_defaults(db, installed_ollama_tags={"gemma3:12b"})
    learner = await get_or_create_owner(db)
    target = "gemma3-12b"
    configured = OllamaProvider("http://127.0.0.1:11434", inference_options={target: OPTIONS})
    gateway = ModelGateway(db, BenchmarkRouter(target), {"ollama": configured}, Budget(0))
    result = await gateway.complete(
        TaskClass.EXPLAIN_SIMPLE,
        MESSAGES,
        learner_id=learner.id,
        response_model=ResearchDiscussion,
        metadata={"structured_output": "native_schema"},
    )
    calls = (
        await db.scalars(
            select(ModelCall)
            .where(ModelCall.request_id == result.request_id)
            .order_by(ModelCall.attempt)
        )
    ).all()
    assert [call.outcome for call in calls] == ["invalid_output", "ok"]
    assert len(posts) == 2
    assert all(
        call.metadata_json["requested_inference_options"]
        == {"reasoning_effort": "low", "temperature": 1.0}
        for call in calls
    )
    handle = StreamHandle()
    text = "".join(
        [
            part
            async for part in gateway.stream(
                TaskClass.EXPLAIN_SIMPLE, MESSAGES, learner_id=learner.id, handle=handle
            )
        ]
    )
    assert text == "Visible answer."
    streamed = await db.scalar(select(ModelCall).where(ModelCall.request_id == handle.request_id))
    assert streamed.metadata_json["requested_inference_options"] == {
        "reasoning_effort": "low",
        "temperature": 1.0,
    }
