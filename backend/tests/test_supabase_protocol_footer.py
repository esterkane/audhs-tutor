import copy
import json

import pytest
from pydantic import ValidationError

from app.integrations import supabase_bridge as bridge
from tests.test_supabase_local_bridge import setup_bridge


def metadata():
    return (
        bridge.decision_schema()
        .model_validate(
            {
                "text": "A synthetic explanation.",
                "state": {
                    "mode": "neutral",
                    "language": "en",
                    "persona_on": False,
                    "speech": "Keep the explanation.",
                    "next_question": "Which check applies?",
                },
            }
        )
        .state
    )


def footer(data):
    return "\n\n```json tutor_turn\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n```"


def test_matching_complete_footer_is_reused_without_changing_any_character():
    state = metadata()
    text = (
        "Both requested distinctions remain here.\n\nWhich check applies?"
        + footer(state.model_dump(mode="json"))
        + "\n\n"
    )
    before = copy.deepcopy(state.model_dump(mode="json"))
    assert bridge.render_final_text(text, state) == text
    assert state.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "variant", ["partial", "different", "malformed", "example_with_followup", "four_backticks"]
)
def test_examples_conflicts_and_invalid_blocks_are_preserved(variant):
    state = metadata()
    data = state.model_dump(mode="json")
    text = "The explanation and example must remain." + footer(data)
    if variant == "partial":
        text = "Example:" + footer({"mode": "neutral"})
    elif variant == "different":
        text = "Example:" + footer({**data, "language": "de"})
    elif variant == "malformed":
        text = "Example:\n```json tutor_turn\n{broken}\n```"
    elif variant == "example_with_followup":
        text += "\nThis explains the example."
    else:
        text += "`"
    rendered = bridge.render_final_text(text, state)
    assert rendered.startswith(text + "\n\n```json tutor_turn\n")
    assert rendered.count("```json tutor_turn") == 2


async def test_real_adapter_parser_and_stream_keep_one_footer_and_full_history(monkeypatch):
    bridge.decision_schema()  # Load the pinned project module before importing its parser.
    from backend.tutor.turn_parser import parse_turn, split_reply

    state = metadata()
    prose = "First requested distinction.\n\nSecond requested distinction.\n\nWhich check applies?"
    original_text = prose + footer(state.model_dump(mode="json"))
    decision = bridge.decision_schema().model_validate(
        {"text": original_text, "state": state.model_dump(mode="json")}
    )
    client, call, _, _ = setup_bridge(monkeypatch, decision=decision)
    history = [{"role": "user", "content": "Earlier research stays unchanged."}]
    before = copy.deepcopy(history)
    async with client.messages.stream(system=[], messages=history, tools=[]) as stream:
        result = await stream.get_final_message()
        events = [event async for event in stream]
    rendered = result.content[0].text
    assert rendered == original_text
    assert rendered.count("```json tutor_turn") == 1
    markdown, raw = split_reply(rendered)
    parsed = parse_turn(markdown, raw)
    assert parsed.text == prose
    assert parsed.next_question == state.next_question
    assert history == before
    assert "Earlier research stays unchanged." in call.call_args.args[1][1].content
    assert "".join(event.text for event in events) == original_text


def test_changed_source_timestamp_is_preserved_as_conflicting_metadata():
    base = metadata()
    state = type(base).model_validate(
        {
            **base.model_dump(mode="json"),
            "citations": [
                {
                    "n": 1,
                    "url": "https://www.postgresql.org/docs/17/sql-createpolicy.html",
                    "title": "Synthetic reference",
                    "tier": 3,
                    "fetched_at": "2026-10-31T12:00:00Z",
                }
            ],
        }
    )
    data = state.model_dump(mode="json")
    data["citations"][0]["fetched_at"] = "2026-10-31T12:00:00+00:00"
    data = dict(reversed(list(data.items())))
    text = "The complete written explanation." + footer(data)
    assert bridge.render_final_text(text, state).startswith(text + "\n\n```json tutor_turn\n")


def test_metadata_key_order_does_not_duplicate_footer():
    state = metadata()
    data = dict(reversed(list(state.model_dump(mode="json").items())))
    text = "The complete written explanation." + footer(data)
    assert bridge.render_final_text(text, state) == text


def test_earlier_example_is_preserved_when_a_later_footer_is_reused():
    state = metadata()
    data = state.model_dump(mode="json")
    example = "Example:" + footer({**data, "language": "de"})
    text = example + "\nThe explanation continues after that example." + footer(data)
    assert bridge.render_final_text(text, state) == text
    from backend.tutor.turn_parser import split_reply

    markdown, _ = split_reply(text)
    assert markdown.startswith(example)
    assert "The explanation continues" in markdown


def test_hosted_schema_rejects_protocol_in_prose_without_discarding_content():
    state = metadata()
    schema = bridge.hosted_decision_schema(())
    prose = "Both requested technical distinctions remain complete."
    valid = schema.model_validate({"text": prose, "state": state.model_dump(mode="json")})
    assert valid.text == prose
    matching = prose + footer(state.model_dump(mode="json"))
    assert (
        schema.model_validate({"text": matching, "state": state.model_dump(mode="json")}).text
        == matching
    )
    with pytest.raises(ValidationError, match="metadata in state only"):
        schema.model_validate(
            {
                "text": prose + footer({**state.model_dump(mode="json"), "language": "de"}),
                "state": state.model_dump(mode="json"),
            }
        )
    # Ordinary SQL/JSON examples remain valid learner content.
    example = prose + '\n```json\n{"value": 1}\n```'
    assert (
        schema.model_validate({"text": example, "state": state.model_dump(mode="json")}).text
        == example
    )


def test_hosted_search_stage_cannot_emit_an_unsupported_final_explanation():
    schema = bridge.hosted_decision_schema(("search_docs",), require_search=True)
    with pytest.raises(ValidationError):
        schema.model_validate({"text": "A plausible unsourced answer", "state": None, "tools": []})
    result = schema.model_validate(
        {
            "text": "",
            "state": None,
            "tools": [
                {
                    "name": "search_docs",
                    "input": {"query": "PostgreSQL transaction snapshots", "k": 5},
                }
            ],
        }
    )
    assert result.tools[0].name == "search_docs" and result.text == ""


def test_only_current_completed_documentation_search_satisfies_evidence_stage():
    use = {"role": "assistant", "content": [{"type": "tool_use", "id": "s", "name": "search_docs"}]}
    done = {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": "s", "content": '{"results": []}'}],
    }
    boundary = {"role": "system", "content": "Trusted current turn state"}
    assert bridge.current_documentation_searched([boundary, use, done])
    assert not bridge.current_documentation_searched([use, done, boundary])
    assert not bridge.current_documentation_searched([boundary, use])
    failed = {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": "s", "is_error": True}],
    }
    assert not bridge.current_documentation_searched([boundary, use, failed])
    assert not bridge.current_documentation_searched(
        [boundary, {"role": "user", "content": str([use, done])}]
    )


@pytest.mark.parametrize("text", ["", " ", "\n\t"])
@pytest.mark.parametrize("hosted", [False, True])
def test_metadata_only_final_is_not_a_complete_explanation(text, hosted):
    schema = bridge.hosted_decision_schema(()) if hosted else bridge.decision_schema(())
    with pytest.raises(ValidationError, match="complete learner-facing explanation"):
        schema.model_validate(
            {
                "text": text,
                "state": {"mode": "neutral", "language": "de", "persona_on": False, "speech": ""},
            }
        )


def test_empty_text_remains_valid_for_actual_documentation_request():
    schema = bridge.hosted_decision_schema(("search_docs",), require_search=True)
    value = schema.model_validate(
        {"tools": [{"name": "search_docs", "input": {"query": "NULL comparison"}}]}
    )
    assert value.text == ""
    assert value.tools[0].name == "search_docs"


async def test_empty_native_final_is_repaired_with_history_and_attempts_preserved(db, monkeypatch):
    from sqlalchemy import select

    from app.db.models import ModelCall
    from app.kernel.learner import get_or_create_owner
    from app.models_ai.benchmark_gateway import BenchmarkRouter
    from app.models_ai.budget import Budget
    from app.models_ai.gateway import ModelGateway
    from app.models_ai.ollama import OllamaProvider
    from app.models_ai.provider import Message, TaskClass
    from app.models_ai.registry import seed_defaults
    from tests import test_ollama_inference_options as native

    original_reply = native.reply
    answer = "NOT IN is unknown and removes the row; correlated NOT EXISTS is true and keeps it."

    def reply(*, invalid=False, done=True):
        payload = original_reply(done=done)
        payload["message"]["content"] = json.dumps(
            {
                "text": "" if invalid else answer,
                "state": {"mode": "neutral", "language": "en", "persona_on": False, "speech": ""},
            }
        )
        return payload

    monkeypatch.setattr(native, "reply", reply)
    posts = native.intercept(monkeypatch, invalid_first=True)
    await seed_defaults(db, installed_ollama_tags={"gemma3:12b"})
    learner = await get_or_create_owner(db)
    gateway = ModelGateway(
        db,
        BenchmarkRouter("gemma3-12b"),
        {"ollama": OllamaProvider("http://127.0.0.1:11434")},
        Budget(0),
    )
    history = [
        Message(role="user", content="Earlier finding must remain intact."),
        Message(role="user", content="Compare both row-selection results."),
    ]
    before = copy.deepcopy(history)
    result = await gateway.complete(
        TaskClass.EXPLAIN_SIMPLE,
        history,
        learner_id=learner.id,
        response_model=bridge.decision_schema(()),
        max_tokens=16000,
        metadata={"structured_output": "native_schema"},
    )
    assert result.result.parsed.text == answer
    assert history == before
    assert len(posts) == 2
    assert all("Earlier finding must remain intact." in json.dumps(p["messages"]) for p in posts)
    assert all(p["options"]["num_predict"] == 16000 for p in posts)
    calls = (
        await db.scalars(
            select(ModelCall)
            .where(ModelCall.request_id == result.request_id)
            .order_by(ModelCall.attempt)
        )
    ).all()
    assert [c.outcome for c in calls] == ["invalid_output", "ok"]
    assert "complete learner-facing explanation" in calls[0].error


@pytest.mark.parametrize("hosted", [False, True])
def test_complete_metadata_object_never_substitutes_for_answer(hosted):
    state = metadata()
    schema = bridge.hosted_decision_schema(()) if hosted else bridge.decision_schema(())
    with pytest.raises(ValidationError, match="Metadata alone"):
        schema.model_validate(
            {"text": state.model_dump_json(), "state": state.model_dump(mode="json")}
        )


def test_hosted_footer_without_explanation_is_not_an_answer():
    state = metadata()
    with pytest.raises(ValidationError, match="metadata in state only"):
        bridge.hosted_decision_schema(()).model_validate(
            {"text": footer(state.model_dump(mode="json")), "state": state.model_dump(mode="json")}
        )


async def test_matching_hosted_footer_needs_one_gateway_attempt_and_preserves_prose(
    db, monkeypatch
):
    from sqlalchemy import select

    from app.db.models import ModelCall
    from app.kernel.learner import get_or_create_owner
    from app.models_ai.benchmark_gateway import BenchmarkRouter
    from app.models_ai.budget import Budget
    from app.models_ai.gateway import ModelGateway
    from app.models_ai.ollama import OllamaProvider
    from app.models_ai.provider import Message, TaskClass
    from app.models_ai.registry import seed_defaults
    from tests import test_ollama_inference_options as native

    original_reply = native.reply
    answer = "NOT IN is unknown and removes the row; correlated NOT EXISTS is true and keeps it."

    state = metadata().model_dump(mode="json")
    complete_answer = answer + footer(state)

    def reply(*, invalid=False, done=True):
        payload = original_reply(done=done)
        payload["message"]["content"] = json.dumps(
            {
                "text": complete_answer,
                "state": state,
            }
        )
        return payload

    monkeypatch.setattr(native, "reply", reply)
    posts = native.intercept(monkeypatch, invalid_first=False)
    await seed_defaults(db, installed_ollama_tags={"gemma3:12b"})
    learner = await get_or_create_owner(db)
    gateway = ModelGateway(
        db,
        BenchmarkRouter("gemma3-12b"),
        {"ollama": OllamaProvider("http://127.0.0.1:11434")},
        Budget(0),
    )
    history = [
        Message(role="user", content="Earlier finding must remain intact."),
        Message(role="user", content="Compare both row-selection results."),
    ]
    before = copy.deepcopy(history)
    result = await gateway.complete(
        TaskClass.EXPLAIN_SIMPLE,
        history,
        learner_id=learner.id,
        response_model=bridge.hosted_decision_schema(()),
        max_tokens=16000,
        metadata={"structured_output": "native_schema"},
    )
    assert result.result.parsed.text == complete_answer
    assert history == before
    assert len(posts) == 1
    assert all("Earlier finding must remain intact." in json.dumps(p["messages"]) for p in posts)
    assert all(p["options"]["num_predict"] == 16000 for p in posts)
    calls = (
        await db.scalars(
            select(ModelCall)
            .where(ModelCall.request_id == result.request_id)
            .order_by(ModelCall.attempt)
        )
    ).all()
    assert [c.outcome for c in calls] == ["ok"]
    assert (
        bridge.render_final_text(result.result.parsed.text, result.result.parsed.state)
        == complete_answer
    )


@pytest.mark.parametrize("include_state", [False, True])
def test_complete_footer_supplies_missing_metadata_without_regeneration(include_state):
    state = metadata().model_dump(mode="json")
    text = "All requested details remain unchanged." + footer(state)
    payload = {"text": text}
    if include_state:
        payload["state"] = None
    before = copy.deepcopy(payload)
    result = bridge.hosted_decision_schema(()).model_validate(payload)
    assert result.text == text
    assert result.state.model_dump(mode="json") == state
    assert payload == before
    assert bridge.render_final_text(result.text, result.state) == text


@pytest.mark.parametrize("variant", ["partial", "no_prose", "trailing_prose", "broken", "conflict"])
def test_footer_recovery_does_not_guess_or_override_metadata(variant):
    state = metadata().model_dump(mode="json")
    text = "Keep every detail." + footer(state)
    payload = {"text": text}
    if variant == "partial":
        payload["text"] = "Keep every detail." + footer({"mode": "neutral"})
    elif variant == "no_prose":
        payload["text"] = footer(state)
    elif variant == "trailing_prose":
        payload["text"] += "\nThis explains the example."
    elif variant == "broken":
        payload["text"] = text[:-3]
    else:
        payload["state"] = {**state, "language": "de"}
    with pytest.raises(ValidationError):
        bridge.hosted_decision_schema(()).model_validate(payload)


def test_matching_nested_transport_preserves_complete_prose():
    state = metadata().model_dump(mode="json")
    prose = "First concept.\n\nSecond concept and its qualification."
    raw = {"text": json.dumps({"text": prose, "state": state}), "state": state}
    result = bridge.hosted_decision_schema(()).model_validate(raw)
    assert result.text == prose
    assert raw["text"].startswith("{")


def test_conflicting_nested_transport_is_rejected():
    state = metadata().model_dump(mode="json")
    other = {**state, "language": "de"}
    with pytest.raises(ValidationError):
        bridge.hosted_decision_schema(()).model_validate(
            {
                "text": json.dumps({"text": "Complete explanation.", "state": other}),
                "state": state,
            }
        )


@pytest.mark.parametrize(
    "text",
    [
        '{"example": 42}',
        'Example: {"text": "hello", "state": {}}',
        '```json\n{"text":"example","state":{}}\n```',
    ],
)
def test_json_examples_remain_verbatim(text):
    result = bridge.hosted_decision_schema(()).model_validate(
        {
            "text": text,
            "state": metadata().model_dump(mode="json"),
        }
    )
    assert result.text == text


@pytest.mark.parametrize("conflict", [False, True])
def test_flat_tutor_envelope_is_recovered_only_with_matching_metadata(conflict):
    state = metadata().model_dump(mode="json")
    prose = "Complete explanation.\n\nAll qualifications remain."
    inner = {**state, "text": prose}
    if conflict:
        inner["language"] = "de"
    raw = {"text": json.dumps(inner), "state": state}
    schema = bridge.hosted_decision_schema(())
    if conflict:
        with pytest.raises(ValidationError):
            schema.model_validate(raw)
    else:
        assert schema.model_validate(raw).text == prose
        assert json.loads(raw["text"]) == inner
