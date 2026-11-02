from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.models_ai.openai_responses import decode_response, request_payload
from app.models_ai.provider import Message, StructuredOutputError


class Answer(BaseModel):
    explanation: str


def response(status="completed", text='{"explanation":"Complete answer"}'):
    return SimpleNamespace(
        status=status,
        output_text=text,
        usage=SimpleNamespace(
            input_tokens=120,
            output_tokens=80,
            input_tokens_details=SimpleNamespace(cached_tokens=90),
            output_tokens_details=SimpleNamespace(reasoning_tokens=60),
        ),
    )


def test_request_preserves_every_message_and_omits_incompatible_sampling():
    messages = [
        Message(role="system", content="Policy"),
        Message(role="user", content="Full question"),
        Message(role="assistant", content="Full prior answer"),
    ]
    before = [m.model_dump() for m in messages]
    payload = request_payload("registered-model", messages, Answer, 4096, "low")
    assert payload["input"] == before
    assert [m.model_dump() for m in messages] == before
    assert payload["max_output_tokens"] == 4096
    assert payload["store"] is False
    assert "temperature" not in payload and "top_p" not in payload
    assert payload["text"]["format"]["schema"]["additionalProperties"] is False


def test_success_accounts_reasoning_tokens_and_cached_input():
    result = decode_response(response(), Answer, "registered-model", 1234)
    assert result.parsed.explanation == "Complete answer"
    assert (result.tokens_in, result.tokens_out, result.cached_tokens) == (120, 80, 90)
    assert result.latency_ms == 1234


@pytest.mark.parametrize(
    "status,text",
    [
        ("incomplete", '{"explanation":"partial"}'),
        ("failed", ""),
        ("completed", ""),
        ("completed", '{"wrong":"field"}'),
    ],
)
def test_unusable_output_is_not_accepted_but_usage_is_preserved(status, text):
    with pytest.raises(StructuredOutputError) as caught:
        decode_response(response(status, text), Answer, "registered-model", 500)
    assert caught.value.attempts == 1
    assert caught.value.tokens_out == 80
    assert caught.value.tokens_in == 120
    assert caught.value.cached_tokens == 90


def test_refusal_is_not_accepted_even_with_valid_json_text():
    raw = response()
    raw.output = [SimpleNamespace(content=[SimpleNamespace(type="refusal")])]
    with pytest.raises(StructuredOutputError) as caught:
        decode_response(raw, Answer, "registered-model", 100)
    assert caught.value.tokens_out == 80


async def test_transport_has_one_attempt_closes_client_and_preserves_input(monkeypatch):
    from unittest.mock import AsyncMock

    from app.models_ai import openai_responses as module
    from app.models_ai.provider import ModelSpec

    created = []
    request = AsyncMock(return_value=response())
    closed = []

    class Client:
        def __init__(self, **kwargs):
            created.append(kwargs)
            self.responses = SimpleNamespace(create=request)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            closed.append(True)

    monkeypatch.setattr(module, "AsyncOpenAI", Client)
    provider = module.OpenAIResponsesProvider("synthetic-key", effort="low")
    monkeypatch.setattr(provider, "validate_local_transport", AsyncMock())
    monkeypatch.setattr(provider, "_validate", lambda *args: None)
    monkeypatch.setattr(module, "check_hosted_messages", lambda *args: None)
    messages = [Message(role="user", content="Complete synthetic question")]
    spec = ModelSpec(registry_id="test", provider="openai", model="test")
    result = await provider.complete(spec, messages, response_model=Answer, max_tokens=4096)
    assert request.await_count == 1 and closed == [True]
    assert created[0]["max_retries"] == 0
    assert request.call_args.kwargs["input"] == [m.model_dump() for m in messages]
    assert result.tokens_out == 80


async def test_unpermitted_or_changed_messages_never_open_transport(monkeypatch):
    from app.models_ai import openai_responses as module
    from app.models_ai.provider import ModelSpec
    from app.models_ai.source_policy import SourcePolicyDenied
    from app.models_ai.study_policy import study_scope

    def forbidden_client(**kwargs):
        raise AssertionError("Denied request reached network construction")

    monkeypatch.setattr(module, "AsyncOpenAI", forbidden_client)
    provider = module.OpenAIResponsesProvider("synthetic-key", effort="low")
    spec = ModelSpec(
        registry_id="openai-luna-study",
        provider="openai",
        model="gpt-6-luna",
        price_in_per_mtok=0.5,
        price_out_per_mtok=0.75,
        context_len=1048576,
    )
    messages = [Message(role="user", content="Approved question")]
    with pytest.raises(SourcePolicyDenied):
        await provider.complete(spec, messages, response_model=Answer)
    with study_scope(spec, messages):
        with pytest.raises(SourcePolicyDenied):
            await provider.complete(
                spec, [Message(role="user", content="Changed question")], response_model=Answer
            )


def test_real_project_schemas_convert_without_losing_fields_or_mutating_input():
    import copy

    from app.integrations.supabase_bridge import hosted_decision_schema
    from app.integrations.supabase_mode import mode_schema, mode_scope
    from app.integrations.supabase_project import project_module

    project_module()
    from backend.tutor.prompt import SessionState

    for search in [True, False]:
        with mode_scope(SessionState(mode="lesson")):
            schema = mode_schema(
                hosted_decision_schema(
                    ("search_docs",) if search else ("search_docs", "web_search"),
                    require_search=search,
                )
            )
        before = copy.deepcopy(schema.model_json_schema())
        payload = request_payload("registered-model", [], schema, 4096, "low")
        wire = payload["text"]["format"]["schema"]
        assert set(wire["properties"]) == set(before["properties"])
        assert set(wire["required"]) == set(wire["properties"])
        assert schema.model_json_schema() == before


def test_disjoint_tool_union_preserves_both_alternatives():
    from app.integrations.supabase_bridge import hosted_decision_schema
    from app.models_ai.openai_responses import compatible_schema

    wire = compatible_schema(hosted_decision_schema(("search_docs", "web_search")))
    union = wire["properties"]["tools"]["items"]
    assert "oneOf" not in union and "discriminator" not in union
    assert len(union["anyOf"]) == 2
    names = {
        wire["$defs"][b["$ref"].split("/")[-1]]["properties"]["name"]["const"]
        for b in union["anyOf"]
    }
    assert names == {"search_docs", "web_search"}


def test_ambiguous_union_is_rejected_instead_of_weakened(monkeypatch):
    from app.models_ai import openai_responses as module

    monkeypatch.setattr(
        module,
        "to_strict_json_schema",
        lambda schema: {"oneOf": [{"type": "number"}, {"type": "integer"}]},
    )
    with pytest.raises(ValueError, match="disjoint"):
        module.compatible_schema(Answer)


class ClaimsAnswer(BaseModel):
    claims: dict[str, object] | None


@pytest.mark.parametrize(
    "claims",
    [
        {"role": "reader", "nested": {"team": [1, True, None]}},
        {},
        {"json": "literal user value", "default": 3},
    ],
)
def test_open_object_values_roundtrip_without_dropping_arbitrary_keys(claims):
    import json

    from app.models_ai.openai_responses import compatible_schema

    wire = compatible_schema(ClaimsAnswer)
    assert wire["properties"]["claims"]["anyOf"][0]["type"] == "string"
    raw = response(text=json.dumps({"claims": json.dumps(claims)}))
    assert decode_response(raw, ClaimsAnswer, "test", 1).parsed.claims == claims


@pytest.mark.parametrize("value", ["[]", '"text"', "broken"])
def test_encoded_nonobjects_are_rejected_with_usage(value):
    import json

    with pytest.raises(StructuredOutputError) as caught:
        decode_response(response(text=json.dumps({"claims": value})), ClaimsAnswer, "test", 1)
    assert caught.value.tokens_out == 80


def test_nullable_open_object_stays_null():
    assert (
        decode_response(response(text='{"claims":null}'), ClaimsAnswer, "test", 1).parsed.claims
        is None
    )


def test_real_tool_claims_decode_before_original_validation():
    import json

    from app.integrations.supabase_bridge import hosted_decision_schema

    schema = hosted_decision_schema(("search_docs", "run_lab_sql"))
    claims = {"sub": "synthetic-user", "app_metadata": {"groups": ["readers"]}}
    raw = response(
        text=json.dumps(
            {
                "text": "",
                "state": None,
                "tools": [
                    {
                        "name": "run_lab_sql",
                        "input": {"sql": "SELECT 1", "claims": json.dumps(claims)},
                    }
                ],
            }
        )
    )
    result = decode_response(raw, schema, "test", 1)
    assert result.parsed.tools[0].input.claims == claims


async def test_stream_never_falls_back_to_chat_completions(monkeypatch):
    from unittest.mock import AsyncMock

    from app.models_ai import openai as chat
    from app.models_ai.openai_responses import OpenAIResponsesProvider
    from app.models_ai.provider import ModelSpec, ProviderError

    transport = AsyncMock(side_effect=AssertionError("Unexpected network request"))
    monkeypatch.setattr(chat.litellm, "acompletion", transport)
    provider = OpenAIResponsesProvider("synthetic-key", effort="medium")
    spec = ModelSpec(registry_id="test", provider="openai", model="test")
    with pytest.raises(ProviderError, match="structured complete only"):
        async for _ in provider.stream(spec, [Message(role="user", content="Question")]):
            pytest.fail("Unsupported streaming emitted content")
    transport.assert_not_called()


class UntaggedAnswer(BaseModel):
    value: str | int


async def test_unsupported_union_is_rejected_before_network(monkeypatch):
    from unittest.mock import AsyncMock

    from app.models_ai import openai_responses as module
    from app.models_ai.provider import ModelSpec

    def forbidden_client(**kwargs):
        raise AssertionError("Unsupported schema reached paid transport")

    monkeypatch.setattr(module, "AsyncOpenAI", forbidden_client)
    provider = module.OpenAIResponsesProvider("synthetic-key", effort="low")
    monkeypatch.setattr(provider, "validate_local_transport", AsyncMock())
    monkeypatch.setattr(provider, "_validate", lambda *args: None)
    monkeypatch.setattr(module, "check_hosted_messages", lambda *args: None)
    with pytest.raises(ValueError, match="Unsupported untagged wire union"):
        await provider.complete(
            ModelSpec(registry_id="test", provider="openai", model="test"),
            [Message(role="user", content="Synthetic question")],
            response_model=UntaggedAnswer,
        )
