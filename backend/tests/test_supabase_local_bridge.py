from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.errors import AppError
from app.integrations import supabase_bridge as bridge


def setup_bridge(monkeypatch, provider="ollama", decision=None):
    db = AsyncMock()
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
            return_value=SimpleNamespace(
                provider=provider, model="test-only", registry_id="test-only"
            )
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
        async with client.messages.stream(system=[], messages=[], tools=[{"name": "read_lab"}]):
            raise AssertionError("Invalid tool must never execute")
    assert error.value.code == "supabase_tool_invalid"
    call.assert_awaited_once()
    db.commit.assert_awaited_once()


async def test_allowed_tool_is_a_request_not_a_claim_of_execution(monkeypatch):
    decision = bridge.LocalDecision(
        tools=[bridge.ToolRequest(name="read_lab", input={"slug": "01"})]
    )
    client, _, _, _ = setup_bridge(monkeypatch, decision=decision)
    async with client.messages.stream(
        system=[], messages=[], tools=[{"name": "read_lab"}]
    ) as stream:
        result = await stream.get_final_message()
    assert result.stop_reason == "tool_use"
    assert result.content[0].type == "tool_use"
    assert result.content[0].input == {"slug": "01"}


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
