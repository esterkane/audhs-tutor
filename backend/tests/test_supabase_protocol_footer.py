import copy
import json

import pytest

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
    decision = bridge.decision_schema().model_validate({"text": original_text, "state": state})
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
