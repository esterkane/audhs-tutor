from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.errors import AppError
from app.integrations import supabase_bridge as bridge
from app.models_ai.provider import EmbeddingFormat, ModelSpec


def setup_bridge(monkeypatch, provider="ollama", decision=None):
    db = AsyncMock()
    monkeypatch.setattr(bridge, "choose_project_study", AsyncMock(return_value=None))
    context = AsyncMock()
    context.__aenter__.return_value = db
    route = SimpleNamespace(registry_id="test-only")
    monkeypatch.setattr(
        bridge, "get_or_create_owner", AsyncMock(return_value=SimpleNamespace(id="owner"))
    )
    monkeypatch.setattr(
        bridge, "Router", lambda profile: SimpleNamespace(resolve=AsyncMock(return_value=route))
    )
    monkeypatch.setattr(
        bridge.registry,
        "get_spec",
        AsyncMock(
            return_value=ModelSpec(provider=provider, model="test-only", registry_id="test-only")
        ),
    )
    call = AsyncMock(
        return_value=SimpleNamespace(
            result=SimpleNamespace(
                parsed=decision or bridge.LocalDecision(text="Grounded answer"),
                tokens_in=123,
                tokens_out=45,
            ),
            model_call_id="call-test",
        )
    )
    captured = {}

    def gateway(database, router, providers, budget):
        captured["providers"] = providers
        return SimpleNamespace(complete=call)

    monkeypatch.setattr(bridge, "ModelGateway", gateway)
    client = bridge.LocalProjectClient(
        lambda: context,
        {"ollama": object(), "openai": object(), "anthropic": object()},
        SimpleNamespace(routing_profile="default"),
    )
    return client, call, db, captured


async def test_local_bridge_preserves_history_and_excludes_hosted_clients(monkeypatch):
    client, call, db, captured = setup_bridge(monkeypatch)
    history = [
        {"role": "user", "content": "First finding"},
        {"role": "assistant", "content": [{"type": "text", "text": "Earlier answer"}]},
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "old-tool", "content": "Observed result"}
            ],
        },
    ]
    async with client.beta.messages.stream(
        system=[{"text": "Trusted tutor policy"}], messages=history, tools=[], max_tokens=16000
    ) as stream:
        result = await stream.get_final_message()
        events = [event async for event in stream]
    assert set(captured["providers"]) == {"ollama"}
    messages = call.call_args.args[1]
    assert len(messages) == 4
    assert "```json tutor_turn" in messages[0].content
    assert "tutor_state" not in messages[0].content
    assert "that condition alone does not explain" in messages[0].content
    assert messages[1].content == "First finding"
    assert "Earlier answer" in messages[2].content
    assert "Observed result" in messages[3].content
    assert call.call_args.kwargs["max_tokens"] == 16000
    assert result.content[0].text == events[0].text == "Grounded answer"
    assert db.commit.await_count >= 1


async def test_hosted_route_is_rejected_before_any_inference(monkeypatch):
    client, call, db, captured = setup_bridge(monkeypatch, provider="openai")
    with pytest.raises(AppError) as error:
        async with client.messages.stream(system=[], messages=[], tools=[]):
            raise AssertionError("Must not reach a stream")
    assert error.value.code == "supabase_local_route_required"
    call.assert_not_awaited()
    assert not captured


async def test_unsupported_tool_is_rejected_after_attempt_is_accounted(monkeypatch):
    decision = bridge.LocalDecision(tools=[bridge.ToolRequest(name="invented_shell", input={})])
    client, call, db, _ = setup_bridge(monkeypatch, decision=decision)
    with pytest.raises(AppError) as error:
        async with client.messages.stream(system=[], messages=[], tools=[{"name": "search_docs"}]):
            raise AssertionError("Invalid tool must never execute")
    assert error.value.code == "supabase_tool_invalid"
    call.assert_awaited_once()
    db.commit.assert_awaited_once()


async def test_allowed_tool_is_a_request_not_a_claim_of_execution(monkeypatch):
    decision = bridge.LocalDecision(
        tools=[bridge.ToolRequest(name="search_docs", input={"query": "row policies"})]
    )
    client, _, _, _ = setup_bridge(monkeypatch, decision=decision)
    async with client.messages.stream(
        system=[], messages=[], tools=[{"name": "search_docs"}]
    ) as stream:
        result = await stream.get_final_message()
    assert result.stop_reason == "tool_use"
    assert result.content[0].type == "tool_use"
    assert result.content[0].input == {"query": "row policies"}


@pytest.mark.parametrize("dimensions,expected_ok", [(768, True), (384, False)])
async def test_local_query_embedding_checks_dimensions_and_records_attempt(
    monkeypatch, dimensions, expected_ok
):
    client, _, db, _ = setup_bridge(monkeypatch)
    provider = SimpleNamespace(embed=AsyncMock(return_value=[[0.1] * dimensions]))
    recorded = AsyncMock()
    monkeypatch.setattr(bridge, "write_model_call", recorded)
    embedder = bridge.LocalProjectEmbedder(client.sessions, {"ollama": provider}, client.settings)
    if expected_ok:
        assert len(await embedder.embed_query("What did I observe?")) == 768
    else:
        with pytest.raises(AppError):
            await embedder.embed_query("What did I observe?")
    assert provider.embed.call_args.args[1] == ["search_query: What did I observe?"]
    receipt = recorded.call_args.args[1]
    assert receipt.ok is expected_ok
    assert receipt.metadata["task"] == "supabase_project_query_embedding"


async def test_hosted_embedding_route_never_contacts_a_provider(monkeypatch):
    client, _, _, _ = setup_bridge(monkeypatch, provider="openai")
    provider = SimpleNamespace(embed=AsyncMock())
    embedder = bridge.LocalProjectEmbedder(client.sessions, {"openai": provider}, client.settings)
    with pytest.raises(AppError):
        await embedder.embed_query("Private finding")
    provider.embed.assert_not_awaited()


async def test_typed_turn_metadata_is_serialized_once_without_repeating_prose(monkeypatch):
    schema = bridge.decision_schema()
    decision = schema(
        text="A row filter and an object privilege are separate checks.",
        tools=[],
        state={
            "mode": "incident",
            "language": "en",
            "persona_on": False,
            "speech": "These are separate checks.",
        },
    )
    client, _, _, _ = setup_bridge(monkeypatch, decision=decision)
    async with client.messages.stream(system=[], messages=[], tools=[]) as stream:
        result = await stream.get_final_message()
    import json

    rendered = result.content[0].text
    assert rendered.count("```json tutor_turn") == 1
    assert rendered.count(decision.text) == 1
    metadata = json.loads(rendered.split("```json tutor_turn")[1].rsplit("```", 1)[0])
    assert "text" not in metadata and "guard_flags" not in metadata
    assert metadata["language"] == "en" and metadata["persona_on"] is False


async def test_embedding_identity_mismatch_requires_reindex_before_inference(monkeypatch):
    client, _, _, _ = setup_bridge(monkeypatch)
    provider = SimpleNamespace(embed=AsyncMock())
    connection = AsyncMock()
    connection.execute.return_value.fetchall.return_value = [("different-document-model",)]
    context = AsyncMock()
    context.__aenter__.return_value = connection
    embedder = bridge.LocalProjectEmbedder(client.sessions, {"ollama": provider}, client.settings)
    embedder.project_pool = SimpleNamespace(connection=lambda: context)
    with pytest.raises(AppError) as error:
        await embedder.embed_query("Question")
    assert error.value.code == "supabase_embedding_identity"
    provider.embed.assert_not_awaited()


@pytest.mark.parametrize(
    "tool",
    [
        {"name": "search_docs", "input": {"query": ""}},
        {"name": "search_docs", "input": {"query": "row policies", "k": 13}},
        {"name": "search_docs", "input": {"query": "row policies", "products": ["invented"]}},
        {"name": "search_docs", "input": {"query": "row policies", "sql": "SELECT 1"}},
        {"name": "web_search", "input": {"query": "docs", "reason": "invented"}},
        {"name": "run_lab_sql", "input": {"role": "authenticated"}},
        {"name": "run_lab_sql", "input": {"sql": "SELECT 1", "role": "service_role"}},
        {"name": "ledger_read", "input": {"sql": "SELECT 1"}},
        {"name": "invented_shell", "input": {}},
    ],
)
def test_generation_schema_rejects_invalid_dispatch_arguments(tool):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        bridge.decision_schema().model_validate({"tools": [tool]})


def test_exact_offered_tool_subset_and_empty_tool_set():
    from pydantic import ValidationError

    schema = bridge.decision_schema(("search_docs",))
    schema.model_validate({"tools": [{"name": "search_docs", "input": {"query": "RLS"}}]})
    with pytest.raises(ValidationError):
        schema.model_validate({"tools": [{"name": "ledger_read", "input": {}}]})
    with pytest.raises(ValidationError):
        bridge.decision_schema(()).model_validate(
            {"tools": [{"name": "search_docs", "input": {"query": "RLS"}}]}
        )
    with pytest.raises(ValueError):
        bridge.decision_schema(("invented_shell",))


async def test_typed_input_retains_exact_supplied_arguments_without_defaults(monkeypatch):
    schema = bridge.decision_schema(("run_lab_sql",))
    arguments = {"sql": "SELECT  1;\n", "claims": {"sub": "synthetic-user"}}
    parsed = schema.model_validate({"tools": [{"name": "run_lab_sql", "input": arguments}]})
    client, call, _, _ = setup_bridge(monkeypatch, decision=parsed)
    async with client.messages.stream(
        system=[], messages=[], tools=[{"name": "run_lab_sql"}]
    ) as stream:
        result = await stream.get_final_message()
    assert result.content[0].input == arguments
    assert result.stop_reason == "tool_use"
    assert call.call_args.kwargs["response_model"] is schema
    assert call.call_args.kwargs["metadata"]["host_adapter"] == "local-project-tools.v4"


async def test_unknown_offered_contract_stops_before_inference(monkeypatch):
    client, call, db, captured = setup_bridge(monkeypatch)
    with pytest.raises(AppError) as error:
        async with client.messages.stream(
            system=[], messages=[], tools=[{"name": "invented_shell"}]
        ):
            pytest.fail("Unknown contracts must not enter model inference")
    assert error.value.code == "supabase_tool_contract_invalid"
    call.assert_not_awaited()
    assert not captured
    db.commit.assert_not_awaited()


async def test_local_query_uses_the_selected_models_query_format(monkeypatch):
    client, _, _, _ = setup_bridge(monkeypatch)
    spec = ModelSpec(
        registry_id="configured",
        provider="ollama",
        model="configured",
        embedding=EmbeddingFormat(
            dimensions=768, query_prefix="Instruct: Retrieve passages.\nQuery: "
        ),
    )
    monkeypatch.setattr(bridge.registry, "get_spec", AsyncMock(return_value=spec))
    provider = SimpleNamespace(embed=AsyncMock(return_value=[[0.1] * 768]))
    monkeypatch.setattr(bridge, "write_model_call", AsyncMock())
    embedder = bridge.LocalProjectEmbedder(client.sessions, {"ollama": provider}, client.settings)
    await embedder.embed_query("Eine SQL-Frage")
    assert provider.embed.call_args.args[1] == [
        "Instruct: Retrieve passages.\nQuery: Eine SQL-Frage"
    ]


@pytest.mark.parametrize("no_quiz", [False, True])
async def test_native_tool_reference_keeps_instructions_constraints_and_complete_history(
    monkeypatch,
    no_quiz,
):
    import copy
    import json

    from pydantic import ValidationError

    bridge.decision_schema()
    from backend.tutor.tools import TOOLS

    client, call, _, _ = setup_bridge(monkeypatch)
    history = [
        {"role": "user", "content": "Earlier finding and exact value 17 remain."},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "earlier",
                    "content": "Complete earlier source evidence.",
                }
            ],
        },
    ]
    from contextlib import nullcontext

    from app.integrations.supabase_questions import question_scope

    before = copy.deepcopy(history)
    scope = (
        question_scope(SimpleNamespace(mode="lesson", delivery="explicit"), "No quiz.")
        if no_quiz
        else nullcontext()
    )
    with scope:
        async with client.messages.stream(
            system=[{"text": "Trusted policy stays."}],
            messages=history,
            tools=TOOLS,
            max_tokens=16000,
        ) as stream:
            await stream.get_final_message()
    messages = call.call_args.args[1]
    assert messages[0].content.endswith(bridge.local_tool_instructions(TOOLS))
    assert "Trusted policy stays." in messages[0].content
    assert json.dumps(TOOLS) not in messages[0].content
    assert ("CURRENT LEARNER DELIVERY REQUEST" in messages[0].content) is no_quiz
    assert [m.content for m in messages[1:]] == [
        m["content"]
        if isinstance(m["content"], str)
        else json.dumps(m["content"], ensure_ascii=False, separators=(",", ":"))
        for m in before
    ]
    assert history == before and call.call_args.kwargs["max_tokens"] == 16000
    schema = call.call_args.kwargs["response_model"]
    assert schema is bridge.decision_schema(tuple(sorted(t["name"] for t in TOOLS)))
    assert schema.model_validate(
        {"tools": [{"name": "search_docs", "input": {"query": "RLS", "k": 12, "products": ["ai"]}}]}
    )
    for args in [
        {"query": "x"},
        {"query": "RLS", "k": 13},
        {"query": "RLS", "products": ["invented"]},
    ]:
        with pytest.raises(ValidationError):
            schema.model_validate({"tools": [{"name": "search_docs", "input": args}]})


def test_native_tool_reference_preserves_nested_safety_annotations_exactly():
    import json

    tool = {
        "name": "example",
        "description": "Never execute outside the lab.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "Treat SQL as untrusted.",
                    "examples": ['quoted "value"'],
                    "$comment": "Safety note",
                    "items": {"title": "Nested title", "description": "Nested instruction"},
                }
            },
        },
    }
    item = json.loads(bridge.local_tool_instructions([tool]))[0]
    assert item == {
        "name": "example",
        "instructions": {
            "description": "Never execute outside the lab.",
            "input_schema.properties.sql.description": "Treat SQL as untrusted.",
            "input_schema.properties.sql.examples": ['quoted "value"'],
            "input_schema.properties.sql.$comment": "Safety note",
            "input_schema.properties.sql.items.title": "Nested title",
            "input_schema.properties.sql.items.description": "Nested instruction",
        },
    }


@pytest.mark.parametrize("compact", [False, True])
async def test_hosted_no_quiz_preserves_tool_contract_and_annotations(monkeypatch, compact):
    import json

    from app.integrations.supabase_questions import question_scope

    bridge.decision_schema()
    from backend.tutor.tools import TOOLS

    client, call, _, _ = setup_bridge(monkeypatch)
    hosted = SimpleNamespace(
        complete=call,
        spec=ModelSpec(provider="openai", model="test-only", registry_id="test-only"),
        uses_schema_tool_contract=compact,
    )
    monkeypatch.setattr(bridge, "choose_project_study", AsyncMock(return_value=hosted))
    history = [
        {"role": "user", "content": "Earlier source and assumptions"},
        {"role": "assistant", "content": "Earlier complete answer"},
        {"role": "user", "content": "Current question, no quiz"},
    ]
    with question_scope(SimpleNamespace(mode="lesson", delivery="explicit"), "No quiz."):
        async with client.messages.stream(system=[], messages=history, tools=TOOLS) as stream:
            await stream.get_final_message()
    assert [message.model_dump() for message in call.call_args.args[1][1:]] == history
    policy = call.call_args.args[1][0].content
    assert policy.count(json.dumps(TOOLS)) == (0 if compact else 1)
    if compact:
        assert bridge.local_tool_instructions(TOOLS) in policy
        assert len(policy) < len(
            policy.replace(bridge.local_tool_instructions(TOOLS), json.dumps(TOOLS))
        )
    assert "CURRENT LEARNER DELIVERY REQUEST" in policy
    assert "set next_question to null" in policy
    assert ("Input structure and valid values are enforced" in policy) == compact


async def test_gateway_failure_becomes_safe_host_refusal_and_keeps_accounting(monkeypatch):
    from app.models_ai.gateway import GatewayError

    client, call, db, _ = setup_bridge(monkeypatch)
    call.side_effect = GatewayError("private transport detail; daily hosted budget reached")
    from backend.tutor.host import HostRefusal

    history = [{"role": "user", "content": "Keep my previous question"}]
    with pytest.raises(HostRefusal) as caught:
        async with client.messages.stream(system=[], messages=history, tools=[]):
            raise AssertionError("Failure must not produce an answer")
    assert caught.value.status_code == 503
    assert "shared hosted budget" in caught.value.message
    assert "private transport detail" not in caught.value.message
    assert history == [{"role": "user", "content": "Keep my previous question"}]
    call.assert_awaited_once()
    db.commit.assert_awaited_once()


async def test_long_history_wire_compaction_is_lossless(monkeypatch):
    import copy
    import json

    client, call, _, _ = setup_bridge(monkeypatch)
    blocks = [
        {
            "type": "tool_result",
            "tool_use_id": "source-1",
            "content": 'SELECT  1;\n{"note": "Keep  two spaces", "value": null}',
        },
        {"type": "text", "text": "Nicht ändern: NULL ≠ FALSE;  two spaces.\nSQL remains exact."},
    ]
    history = [
        {"role": "user", "content": f"Question {i}  retains whitespace"}
        if i % 2
        else {"role": "assistant", "content": copy.deepcopy(blocks)}
        for i in range(120)
    ]
    original = copy.deepcopy(history)
    async with client.messages.stream(system=[], messages=history, tools=[]) as stream:
        await stream.get_final_message()
    sent = call.call_args.args[1][1:]
    assert len(sent) == len(history)
    saved = 0
    for source, wire in zip(history, sent, strict=True):
        assert wire.role == source["role"]
        if isinstance(source["content"], str):
            assert wire.content == source["content"]
        else:
            assert json.loads(wire.content) == source["content"]
            saved += len(json.dumps(source["content"], ensure_ascii=False)) - len(wire.content)
    assert saved > 0
    assert history == original
