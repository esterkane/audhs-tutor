"""No inference network is used: transport spies and disposable databases only."""

from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import select

from app.db.models import BudgetReservation, ModelCall
from app.models_ai import registry
from app.models_ai.benchmark_gateway import BenchmarkRouter
from app.models_ai.budget import Budget
from app.models_ai.claude import ClaudeProvider
from app.models_ai.fake import FakeProvider
from app.models_ai.gateway import GatewayError, ModelGateway, StreamHandle
from app.models_ai.ollama import OllamaProvider
from app.models_ai.openai import OpenAIProvider
from app.models_ai.provider import Message, ModelSpec, TaskClass
from app.models_ai.source_policy import SourcePolicyDenied, validate_transport

SPEC = ModelSpec(registry_id="untrusted-label", provider="fake", model="untrusted-model")
MESSAGES = [Message(role="user", content="Private course context and owner question")]


@pytest.mark.parametrize("adapter", [OpenAIProvider, ClaudeProvider])
@pytest.mark.parametrize("stream", [False, True])
async def test_direct_hosted_denied_before_sdk(adapter, stream, monkeypatch):
    call = AsyncMock(side_effect=AssertionError("must not transmit"))
    monkeypatch.setattr("litellm.acompletion", call)
    provider = adapter("synthetic-not-a-credential")
    with pytest.raises(SourcePolicyDenied, match="owner-origin"):
        if stream:
            _ = [part async for part in provider.stream(SPEC, MESSAGES)]
        else:
            await provider.complete(SPEC, MESSAGES, metadata={"owner_authored": True})
    call.assert_not_called()


async def test_unknown_transport_is_denied():
    with pytest.raises(SourcePolicyDenied):
        await validate_transport(object(), SPEC)


@pytest.mark.parametrize("stream", [False, True])
async def test_gateway_denial_has_no_reservation_or_model_call(db, stream):
    await registry.seed_defaults(db, installed_ollama_tags={"hosted"})
    gateway = ModelGateway(
        db,
        BenchmarkRouter("hosted-strong"),
        {"anthropic": ClaudeProvider("synthetic")},
        Budget(10),
    )
    reserve = AsyncMock(side_effect=AssertionError("must not reserve"))
    gateway._reserve = reserve
    with pytest.raises(GatewayError, match="Source policy"):
        if stream:
            _ = [
                part
                async for part in gateway.stream(TaskClass.CHAT, MESSAGES, handle=StreamHandle())
            ]
        else:
            await gateway.complete(TaskClass.CHAT, MESSAGES)
    reserve.assert_not_called()
    assert not (await db.scalars(select(BudgetReservation))).all()
    assert not (await db.scalars(select(ModelCall))).all()


@pytest.mark.parametrize(
    "host",
    [
        "https://remote.example",
        "http://localhost@remote.example",
        "http://localhost/proxy",
        "http://localhost?upstream=remote",
    ],
)
async def test_remote_ollama_never_probes_or_transmits(host, monkeypatch):
    call = AsyncMock(side_effect=AssertionError("must not transmit"))
    monkeypatch.setattr(httpx.AsyncClient, "post", call)
    with pytest.raises(SourcePolicyDenied):
        await OllamaProvider(host).embed(SPEC, ["Private source"])
    call.assert_not_called()


@pytest.mark.parametrize(
    "details",
    [
        {},
        {"model_info": {"size": 1}, "remote_host": "cloud"},
        {"model_info": {"size": 1}, "remote_model": "cloud"},
        [],
    ],
)
@pytest.mark.parametrize("operation", ["complete", "stream", "embed", "generate_stats"])
async def test_cloud_or_unknown_ollama_denied(details, operation, monkeypatch):
    post = AsyncMock(
        return_value=httpx.Response(
            200, json=details, request=httpx.Request("POST", "http://localhost/api/show")
        )
    )
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    call = AsyncMock(side_effect=AssertionError("must not infer"))
    monkeypatch.setattr("litellm.acompletion", call)
    provider = OllamaProvider("http://localhost:11434")
    with pytest.raises(SourcePolicyDenied):
        if operation == "stream":
            _ = [part async for part in provider.stream(SPEC, MESSAGES)]
        elif operation == "complete":
            await provider.complete(SPEC, MESSAGES)
        elif operation == "embed":
            await provider.embed(SPEC, ["Private source"])
        else:
            await provider.generate_stats(SPEC, "Private source")
    call.assert_not_called()
    assert post.await_count == 1
    assert post.call_args.kwargs["json"] == {"model": SPEC.model}


async def test_fake_transport_does_not_depend_on_registry_provider_label():
    provider = FakeProvider()
    await validate_transport(provider, SPEC.model_copy(update={"provider": "anthropic"}))
    assert (await provider.complete(SPEC, MESSAGES)).text == "fake answer"
    assert provider.calls[0].messages == MESSAGES


@pytest.mark.parametrize("stream", [False, True])
async def test_denied_primary_falls_back_without_dropping_context(db, stream):
    class LocalFallback(BenchmarkRouter):
        def chain_for(self, task, override=None):
            return ["hosted-strong", "llama31-8b"]

    await registry.seed_defaults(db, installed_ollama_tags={"hosted", "llama3.1:8b"})
    local = FakeProvider()
    gateway = ModelGateway(
        db,
        LocalFallback("unused"),
        {
            "anthropic": ClaudeProvider("synthetic"),
            "ollama": local,
        },
        Budget(10),
    )
    if stream:
        assert "".join(
            [p async for p in gateway.stream(TaskClass.CHAT, MESSAGES, handle=StreamHandle())]
        )
    else:
        await gateway.complete(TaskClass.CHAT, MESSAGES)
    assert local.calls[0].messages == MESSAGES
    assert not (await db.scalars(select(BudgetReservation))).all()
    calls = (await db.scalars(select(ModelCall))).all()
    assert len(calls) == 1
    assert calls[0].registry_id == "llama31-8b"


async def test_sdk_transport_ignores_proxy_and_disables_redirects(monkeypatch):
    from app.models_ai.ollama import _local_sdk_client

    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.2:9999")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.2:9999")
    monkeypatch.delenv("NO_PROXY", raising=False)
    async with _local_sdk_client(1) as handler:
        client = handler.client
        assert client.trust_env is False
        assert client.follow_redirects is False
        assert client._mounts == {}  # no environment-proxy routing
    assert client.is_closed


async def test_native_ollama_payload_transport_is_pinned(monkeypatch):
    clients = []
    original = httpx.AsyncClient

    def client_factory(**kwargs):
        clients.append(kwargs)

        def respond(request):
            if request.url.path == "/api/show":
                return httpx.Response(200, json={"model_info": {"size": 1}})
            if request.url.path == "/api/embed":
                return httpx.Response(200, json={"embeddings": [[1.0]]})
            return httpx.Response(200, json={"eval_count": 1, "eval_duration": 1})

        return original(**kwargs, transport=httpx.MockTransport(respond))

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    provider = OllamaProvider("http://localhost:11434")
    assert await provider.embed(SPEC, ["private source"]) == [[1.0]]
    await provider.generate_stats(SPEC, "private source")
    assert len(clients) == 4
    assert all(c["trust_env"] is False and c["follow_redirects"] is False for c in clients)


async def test_transport_rechecked_before_structured_repair(db):
    from pydantic import BaseModel

    class Answer(BaseModel):
        text: str

    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    provider = FakeProvider(fail_structured_times=1)
    checks = 0

    async def validate(spec):
        nonlocal checks
        checks += 1
        if checks > 1:
            raise SourcePolicyDenied("Source policy: transport no longer verified")

    provider.validate_local_transport = validate
    gateway = ModelGateway(db, BenchmarkRouter("llama31-8b"), {"ollama": provider}, Budget(1))
    with pytest.raises(GatewayError, match="no longer verified"):
        await gateway.complete(TaskClass.CHAT, MESSAGES, response_model=Answer)
    assert checks == 2
    assert len(provider.calls) == 1
    assert not (await db.scalars(select(BudgetReservation))).all()
