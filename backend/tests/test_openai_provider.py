from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from litellm import ModelResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.db.models import ModelCall
from app.models_ai import manage, registry
from app.models_ai.benchmark_gateway import BenchmarkRouter
from app.models_ai.budget import Budget
from app.models_ai.factory import build_providers
from app.models_ai.fake import FakeProvider
from app.models_ai.gateway import GatewayError, ModelGateway, StreamHandle
from app.models_ai.openai import OpenAIProvider
from app.models_ai.provider import Message, ModelSpec, ProviderError, StreamUsage, TaskClass

MESSAGES = [Message(role="system", content="Tutor policy"), Message(role="user", content="hint")]
SPEC = ModelSpec(
    registry_id="openai-luna",
    provider="openai",
    model="gpt-6-luna",
    price_in_per_mtok=0.125,
    price_out_per_mtok=0.5,
)


async def test_plain_completion_is_explicit_and_accounts_usage(monkeypatch):
    seen = []

    async def complete(**kwargs):
        seen.append(kwargs)
        return ModelResponse(
            choices=[{"message": {"role": "assistant", "content": "Try tracing it."}}],
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 30,
                "prompt_tokens_details": {"cached_tokens": 20},
            },
        )

    monkeypatch.setattr("app.models_ai.openai.litellm.acompletion", complete)
    out = await OpenAIProvider("test-key").complete(SPEC, MESSAGES, max_tokens=200)
    assert (out.tokens_in, out.tokens_out, out.cached_tokens) == (100, 30, 20)
    assert out.provider == "openai" and out.reported_cost_usd is None
    assert seen[0]["messages"][0] == {"role": "system", "content": "Tutor policy"}
    assert seen[0]["reasoning_effort"] == "none"
    assert seen[0]["num_retries"] == 0 and seen[0]["store"] is False
    assert seen[0]["max_completion_tokens"] == 200
    assert seen[0]["api_base"] == "https://api.openai.com/v1"


async def test_structured_one_attempt_and_usage(monkeypatch):
    class Answer(BaseModel):
        hint: str

    p = OpenAIProvider("test-key")
    call = AsyncMock(
        return_value=(
            Answer(hint="Trace x"),
            ModelResponse(usage={"prompt_tokens": 80, "completion_tokens": 15}),
        )
    )
    monkeypatch.setattr(p._instructor.chat.completions, "create_with_completion", call)
    out = await p.complete(SPEC, MESSAGES, response_model=Answer, max_retries=8)
    assert out.parsed.hint == "Trace x" and out.tokens_out == 15
    assert call.call_args.kwargs["max_retries"] == 1


async def test_stream_final_usage_chunk(monkeypatch):
    async def chunks():
        yield SimpleNamespace(
            usage=None, choices=[SimpleNamespace(delta=SimpleNamespace(content="Hi"))]
        )
        yield SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=50, completion_tokens=4), choices=[]
        )

    async def complete(**kwargs):
        assert kwargs["stream_options"] == {"include_usage": True}
        assert kwargs["reasoning_effort"] == "none" and kwargs["num_retries"] == 0
        return chunks()

    monkeypatch.setattr("app.models_ai.openai.litellm.acompletion", complete)
    result = [x async for x in OpenAIProvider("test-key").stream(SPEC, MESSAGES)]
    assert result == ["Hi", StreamUsage(tokens_in=50, tokens_out=4)]


async def test_error_redacts_key_and_oversized_prompt_never_calls(monkeypatch):
    call = AsyncMock(side_effect=RuntimeError("secret-key in HTTP error"))
    monkeypatch.setattr("app.models_ai.openai.litellm.acompletion", call)
    p = OpenAIProvider("secret-key")
    with pytest.raises(ProviderError) as e:
        await p.complete(SPEC, MESSAGES)
    assert "secret-key" not in str(e.value)
    with pytest.raises(ProviderError, match="too large"):
        await p.complete(SPEC, [Message(role="user", content="x" * 100_001)])
    assert call.await_count == 1


async def test_keys_are_independent_and_custom_readiness_refreshes(db, settings, monkeypatch):
    monkeypatch.setattr(manage, "installed_models", AsyncMock(return_value=set()))
    settings.openai_api_key = "test-key"
    providers = build_providers(settings)
    assert "openai" in providers and "anthropic" not in providers
    await manage.seed(db, settings)
    assert (await registry.get_row(db, "openai-luna")).status == "ready"
    assert (await registry.get_row(db, "hosted-medium")).status == "available"
    await manage.add(
        db,
        settings,
        source="openai",
        repo_id="custom",
        tag="gpt-6-luna",
        registry_id="custom",
        price_in=1,
        price_out=2,
    )
    settings.openai_api_key = ""
    await manage.seed(db, settings)
    assert (await registry.get_row(db, "custom")).status == "available"
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        await manage.pull(db, settings, "openai-luna")
    assert (await registry.get_row(db, "openai-luna")).status == "available"


async def test_custom_openai_requires_known_positive_prices(db, settings):
    for value in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="positive finite"):
            await manage.add(
                db,
                settings,
                source="openai",
                repo_id="x",
                tag="gpt-6-luna",
                price_in=value,
                price_out=1,
            )


async def test_gateway_counts_openai_spend_and_blocks_before_request(db):
    await registry.seed_defaults(db, installed_ollama_tags={"openai"})
    fake = FakeProvider(text="Try tracing x", tokens_in=100, tokens_out=40)
    budget = Budget(1)
    gw = ModelGateway(db, BenchmarkRouter("openai-luna"), {"openai": fake}, budget)
    result = await gw.complete(TaskClass.HINT, MESSAGES)
    assert result.hosted and result.cost_status == "estimated" and result.cost_usd > 0
    assert (await budget.spend_today(db)).counted == pytest.approx(result.cost_usd, abs=1e-6)
    budget.daily_cap_usd = 0
    with pytest.raises(GatewayError):
        await gw.complete(TaskClass.HINT, MESSAGES)
    calls = (await db.execute(select(ModelCall))).scalars().all()
    assert len(calls) == 2 and {c.outcome for c in calls} == {"ok", "blocked"}
    assert all(c.provider == "openai" for c in calls)
    assert len(fake.calls) == 1


async def test_hosted_benchmark_respects_cap_and_records_each_call(db, settings, monkeypatch):
    await registry.seed_defaults(db, installed_ollama_tags={"openai"})
    fake = FakeProvider(text="Trace x. What comes next?", tokens_in=100, tokens_out=20)
    monkeypatch.setattr(manage, "build_providers", lambda _: {"openai": fake})
    settings.daily_budget_usd = 0
    with pytest.raises(GatewayError):
        await manage.bench(db, settings, "openai-luna")
    assert not fake.calls
    assert not (await registry.get_row(db, "openai-luna")).benchmark_json
    settings.daily_budget_usd = 1
    result = await manage.bench(db, settings, "openai-luna")
    assert result["tutoring_hard_checks"]["total"] == 15
    calls = (await db.execute(select(ModelCall))).scalars().all()
    assert len(calls) == 7  # blocked stream, then stream + five tutoring calls
    assert all(c.provider == "openai" for c in calls)
    assert all(c.cost_status != "free" for c in calls if c.outcome != "blocked")


async def test_stream_charged_and_failure_unknown_not_free(db):
    await registry.seed_defaults(db, installed_ollama_tags={"openai"})
    fake = FakeProvider(text="Trace x", tokens_in=100, tokens_out=20)
    gw = ModelGateway(db, BenchmarkRouter("openai-luna"), {"openai": fake}, Budget(1))
    text = "".join([c async for c in gw.stream(TaskClass.CHAT, MESSAGES, handle=StreamHandle())])
    assert text
    fake.fail_times = 1
    with pytest.raises(GatewayError):
        await gw.complete(TaskClass.CHAT, MESSAGES)
    calls = (await db.execute(select(ModelCall))).scalars().all()
    assert calls[-1].cost_status == "unknown" and calls[-1].reserved_usd > 0
    assert calls[0].cost_usd > 0


async def test_large_schema_reservation_blocks_before_call(db):
    from pydantic import Field, create_model

    await registry.seed_defaults(db, installed_ollama_tags={"openai"})
    fake = FakeProvider()
    schema = create_model("Large", answer=(str, Field(description="x" * 20000)))
    gw = ModelGateway(db, BenchmarkRouter("openai-luna"), {"openai": fake}, Budget(0.001))
    with pytest.raises(GatewayError):
        await gw.complete(TaskClass.FORMAT, MESSAGES, response_model=schema, max_tokens=10)
    assert not fake.calls


async def test_stopped_stream_keeps_reserved_billing_and_closes(db):
    await registry.seed_defaults(db, installed_ollama_tags={"openai"})
    closed = []

    class Partial(FakeProvider):
        async def stream(self, *args, **kwargs):
            try:
                yield "first"
                yield "second"
            finally:
                closed.append(True)

    budget = Budget(1)
    gw = ModelGateway(db, BenchmarkRouter("openai-luna"), {"openai": Partial()}, budget)
    stream = gw.stream(TaskClass.CHAT, MESSAGES, handle=StreamHandle())
    assert await anext(stream) == "first"
    await stream.aclose()
    row = (await db.execute(select(ModelCall))).scalar_one()
    assert row.outcome == "cancelled" and row.cost_status == "unknown"
    assert closed == [True]
    assert (await budget.spend_today(db)).counted == pytest.approx(row.reserved_usd)


async def test_adapter_closes_transport_when_stopped(monkeypatch):
    closed = []

    async def chunks():
        try:
            yield SimpleNamespace(
                usage=None, choices=[SimpleNamespace(delta=SimpleNamespace(content="Hi"))]
            )
            yield SimpleNamespace(usage=None, choices=[])
        finally:
            closed.append(True)

    async def complete(**kwargs):
        return chunks()

    monkeypatch.setattr("app.models_ai.openai.litellm.acompletion", complete)
    stream = OpenAIProvider("test-key").stream(SPEC, MESSAGES)
    assert await anext(stream) == "Hi"
    await stream.aclose()
    assert closed == [True]
