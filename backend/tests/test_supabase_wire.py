import copy
import json

import pytest

from app.integrations import supabase_wire as wire


def envelope():
    return {
        "results": [
            {
                "url": "https://example.test/source",
                "title": "Row security",
                "heading_path": "Database > Row security",
                "tier": 1,
                "fetched_at": None,
                "score": 0.125,
                "content": 'SELECT  1;\nNULL ≠ FALSE; {"quoted": "  unchanged"}',
            }
        ]
    }


def request(body=None):
    return [
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "lookup-1", "name": "search_docs", "input": {}},
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "lookup-1",
                    "content": body
                    if body is not None
                    else json.dumps(envelope(), ensure_ascii=False),
                    "is_error": False,
                },
            ],
        },
    ]


def test_canonical_search_result_retains_all_values_and_original_history():
    history = request()
    original = copy.deepcopy(history)
    messages = wire.message_contents(history)
    result = json.loads(messages[1])[0]
    assert json.loads(result["content"]) == envelope()
    assert result["tool_use_id"] == "lookup-1" and result["is_error"] is False
    assert len(result["content"]) < len(original[1]["content"][0]["content"])
    assert history == original
    assert json.loads(messages[0]) == original[0]["content"]


@pytest.mark.parametrize(
    "change",
    [
        "missing_call",
        "later_call",
        "wrong_tool",
        "user_call",
        "assistant_result",
        "error",
        "missing_success",
        "duplicate_call",
        "later_duplicate_call",
        "duplicate_result",
        "later_duplicate_result",
        "missing_id",
        "unknown_id",
    ],
)
def test_ambiguous_or_unmatched_results_stay_exact(change):
    history = request()
    if change == "missing_call":
        history = history[1:]
    elif change == "later_call":
        history.reverse()
    elif change == "wrong_tool":
        history[0]["content"][0]["name"] = "run_lab_sql"
    elif change == "user_call":
        history[0]["role"] = "user"
    elif change == "assistant_result":
        history[1]["role"] = "assistant"
    elif change == "error":
        history[1]["content"][0]["is_error"] = True
    elif change == "missing_success":
        del history[1]["content"][0]["is_error"]
    elif change == "duplicate_call":
        history[0]["content"].append(copy.deepcopy(history[0]["content"][0]))
    elif change == "later_duplicate_call":
        history.append(copy.deepcopy(history[0]))
    elif change == "duplicate_result":
        history[1]["content"].append(copy.deepcopy(history[1]["content"][0]))
    elif change == "later_duplicate_result":
        history.append(copy.deepcopy(history[1]))
    elif change == "missing_id":
        del history[1]["content"][0]["tool_use_id"]
    elif change == "unknown_id":
        history[1]["content"][0]["tool_use_id"] = "unknown"
    before = copy.deepcopy(history)
    result = wire.message_contents(history)
    assert [json.loads(content) for content in result] == [m["content"] for m in history]
    assert history == before


@pytest.mark.parametrize(
    "body",
    [
        '{"results": [], "results": []}',
        '{"results": [], "score": 1.000}',
        '{"results": [], "value": NaN}',
        '{"results": [], "value": Infinity}',
        "{not JSON}",
        '{"results":[]}',
        "SELECT  1;",
        "<untrusted_source> preserve  spaces </untrusted_source>",
        '{"data": {"value": 1}}',
        "[]",
        '{"results": [1]}',
        '{"results": [{"url": "x"}]}',
    ],
)
def test_noncanonical_plain_or_wrong_envelope_is_untouched(body):
    history = request(body)
    assert [json.loads(c) for c in wire.message_contents(history)] == [
        m["content"] for m in history
    ]


def test_large_body_skips_json_parser(monkeypatch):
    history = request("{" + " " * wire.MAX_TOOL_RESULT_CHARS)

    def forbidden(_body):
        raise AssertionError("Oversized body must not be parsed")

    monkeypatch.setattr(wire.json, "loads", forbidden)
    assert wire.message_contents(history)[1] == wire.message_content(history[1]["content"])


def test_empty_search_results_are_supported():
    history = request(json.dumps({"results": [], "note": "No corpus hits."}))
    result = json.loads(wire.message_contents(history)[1])[0]["content"]
    assert result == '{"results":[],"note":"No corpus hits."}'


def test_no_provenance_and_learner_assistant_json_are_not_rewritten():
    body = json.dumps(envelope(), ensure_ascii=False)
    assert wire.message_content(body) == body
    blocks = [
        {"type": "tool_result", "content": body},
        {"type": "text", "text": body},
        {"type": "tool_use", "input": {"sql": body}},
    ]
    assert json.loads(wire.message_content(blocks)) == blocks


@pytest.mark.parametrize("score", ["1.000", "NaN", "Infinity", "-Infinity", "-0"])
def test_search_envelope_with_noncanonical_number_stays_exact(score):
    body = json.dumps(envelope(), ensure_ascii=False).replace('"score": 0.125', f'"score": {score}')
    history = request(body)
    result = json.loads(wire.message_contents(history)[1])
    assert result == history[1]["content"]


def test_later_wrong_role_id_collision_disables_earlier_compaction():
    history = request()
    history.append(
        {
            "role": "user",
            "content": [
                {"type": "tool_use", "id": "lookup-1", "name": "search_docs", "input": {}},
            ],
        }
    )
    assert [json.loads(c) for c in wire.message_contents(history)] == [
        message["content"] for message in history
    ]
