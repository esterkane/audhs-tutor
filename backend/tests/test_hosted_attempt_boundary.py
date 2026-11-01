"""Exercise the real installed Instructor adapter, with offline model responses."""

import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from litellm import ModelResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.db.models import ModelCall
from app.models_ai import registry
from app.models_ai.benchmark_gateway import BenchmarkRouter
from app.models_ai.budget import Budget
from app.models_ai.claude import ClaudeProvider
from app.models_ai.gateway import ModelGateway
from app.models_ai.openai import OpenAIProvider
from app.models_ai.provider import Message, ModelSpec, StructuredOutputError, TaskClass


class CheckedAnswer(BaseModel):
    hint: str = Field(min_length=1)


CASES = [
    (OpenAIProvider, "openai", "openai-luna", "gpt-6-luna"),
    (ClaudeProvider, "anthropic", "hosted-strong", "claude-sonnet-5"),
]
MESSAGES = [
    Message(role="system", content="Preserve source and all earlier findings."),
    Message(role="user", content="Earlier finding: equality and identity differ."),
]


def prepare(monkeypatch, cls, on_first=None, enforce_policy=False):
    if not enforce_policy:
        monkeypatch.setattr(cls, "validate_local_transport", AsyncMock())
        monkeypatch.setattr("app.models_ai.openai.check_hosted_messages", lambda *_: None)
        monkeypatch.setattr("app.models_ai.claude.check_hosted_messages", lambda *_: None)
    calls = []

    async def complete(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        assert kwargs["num_retries"] == 0
        if len(calls) == 1 and on_first is not None:
            on_first()
        return ModelResponse(
            model=kwargs["model"],
            choices=[
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "synthetic_call",
                                "type": "function",
                                "function": {
                                    "name": "CheckedAnswer",
                                    "arguments": json.dumps(
                                        {
                                            "hint": ""
                                            if len(calls) == 1
                                            else "Compare equality separately from identity."
                                        }
                                    ),
                                },
                            }
                        ],
                    },
                }
            ],
            usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        )

    monkeypatch.setattr("app.models_ai.openai.litellm.acompletion", complete)
    return cls("synthetic-test-key"), calls


@pytest.mark.parametrize("cls,provider,identity,model", CASES)
async def test_provider_does_not_hide_a_second_validation_attempt(
    monkeypatch, cls, provider, identity, model
):
    adapter, calls = prepare(monkeypatch, cls)
    spec = ModelSpec(
        registry_id=identity,
        provider=provider,
        model=model,
        price_in_per_mtok=0.125,
        price_out_per_mtok=0.5,
    )
    with pytest.raises(StructuredOutputError) as failed:
        await adapter.complete(spec, MESSAGES, response_model=CheckedAnswer, max_retries=8)
    assert len(calls) == 1
    assert failed.value.attempts == 1
    assert (failed.value.tokens_in, failed.value.tokens_out) == (100, 20)


@pytest.mark.parametrize("cls,provider,identity,model", CASES)
async def test_gateway_records_and_charges_each_actual_sdk_attempt(
    db, monkeypatch, cls, provider, identity, model
):
    adapter, calls = prepare(monkeypatch, cls)
    await registry.seed_defaults(db, installed_ollama_tags={"openai", "hosted"})
    budget = Budget(1)
    gateway = ModelGateway(db, BenchmarkRouter(identity), {provider: adapter}, budget)
    history = copy.deepcopy(MESSAGES)
    result = await gateway.complete(
        TaskClass.HINT, history, response_model=CheckedAnswer, max_tokens=200
    )
    rows = (
        await db.scalars(
            select(ModelCall)
            .where(ModelCall.request_id == result.request_id)
            .order_by(ModelCall.attempt)
        )
    ).all()
    assert [row.outcome for row in rows] == ["invalid_output", "ok"]
    assert len(calls) == len(rows) == 2
    assert all((row.tokens_in, row.tokens_out) == (100, 20) for row in rows)
    assert all(row.cost_usd > 0 for row in rows)
    assert (await budget.spend_today(db)).counted == pytest.approx(
        sum(row.cost_usd for row in rows), abs=1e-6
    )
    assert history == MESSAGES
    assert all(
        "Earlier finding: equality and identity differ." in json.dumps(call["messages"])
        for call in calls
    )


@pytest.mark.parametrize("cls,provider,identity,model", CASES)
async def test_changed_budget_is_checked_before_a_validation_repair(
    db, monkeypatch, cls, provider, identity, model
):
    from app.models_ai.gateway import GatewayError

    budget = Budget(1)
    adapter, calls = prepare(monkeypatch, cls, lambda: setattr(budget, "daily_cap_usd", 0))
    await registry.seed_defaults(db, installed_ollama_tags={"openai", "hosted"})
    gateway = ModelGateway(db, BenchmarkRouter(identity), {provider: adapter}, budget)
    with pytest.raises(GatewayError):
        await gateway.complete(
            TaskClass.HINT, MESSAGES, response_model=CheckedAnswer, max_tokens=200
        )
    assert len(calls) == 1
    rows = (await db.scalars(select(ModelCall).order_by(ModelCall.attempt))).all()
    assert [row.outcome for row in rows] == ["invalid_output", "blocked"]
    assert rows[0].cost_usd > 0


@pytest.mark.parametrize("cls,provider,identity,model", CASES)
async def test_stream_keeps_transport_retries_disabled(monkeypatch, cls, provider, identity, model):
    adapter, calls = prepare(monkeypatch, cls)

    async def chunks():
        yield SimpleNamespace(
            usage=None, choices=[SimpleNamespace(delta=SimpleNamespace(content="Complete answer."))]
        )
        yield SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20), choices=[]
        )

    async def stream(**kwargs):
        assert kwargs["num_retries"] == 0
        calls.append(kwargs)
        return chunks()

    monkeypatch.setattr("app.models_ai.openai.litellm.acompletion", stream)
    spec = ModelSpec(
        registry_id=identity,
        provider=provider,
        model=model,
        price_in_per_mtok=0.125,
        price_out_per_mtok=0.5,
    )
    parts = [part async for part in adapter.stream(spec, MESSAGES)]
    assert len(calls) == 1
    assert "".join(part for part in parts if isinstance(part, str)) == "Complete answer."


@pytest.mark.parametrize("cls,provider,identity,model", CASES)
async def test_real_study_permission_survives_only_gateway_bound_repairs(
    db, monkeypatch, cls, provider, identity, model
):
    from app.models_ai.study_policy import study_scope, study_scope_active

    adapter, calls = prepare(monkeypatch, cls, enforce_policy=True)
    await registry.seed_defaults(db, installed_ollama_tags={"openai", "hosted"})
    spec = await registry.get_spec(db, identity)
    gateway = ModelGateway(db, BenchmarkRouter(identity), {provider: adapter}, Budget(1))
    with study_scope(spec, MESSAGES):
        result = await gateway.complete(
            TaskClass.EXPLAIN_SIMPLE, MESSAGES, response_model=CheckedAnswer, max_tokens=200
        )
    assert result.result.parsed.hint == "Compare equality separately from identity."
    assert len(calls) == 2
    rows = (
        await db.scalars(
            select(ModelCall)
            .where(ModelCall.request_id == result.request_id)
            .order_by(ModelCall.attempt)
        )
    ).all()
    assert [r.outcome for r in rows] == ["invalid_output", "ok"]
    assert not study_scope_active()
