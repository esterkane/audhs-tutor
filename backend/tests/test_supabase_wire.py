import copy
import json

import pytest

from app.integrations.supabase_wire import message_content


def test_canonical_tool_json_retains_all_values_and_original_history():
    evidence = {
        "results": [
            {
                "url": "https://example.test/source",
                "tier": 1,
                "text": 'SELECT  1;\nNULL ≠ FALSE; {"quoted": "  unchanged"}',
                "count": 9007199254740993,
                "score": 0.125,
            }
        ],
        "empty": None,
    }
    body = json.dumps(evidence, ensure_ascii=False)
    history = [
        {"type": "tool_result", "tool_use_id": "lookup-1", "content": body, "is_error": False}
    ]
    before = copy.deepcopy(history)
    wire = json.loads(message_content(history))
    assert json.loads(wire[0]["content"]) == evidence
    assert wire[0]["tool_use_id"] == "lookup-1"
    assert wire[0]["is_error"] is False
    assert len(wire[0]["content"]) < len(body)
    assert history == before


@pytest.mark.parametrize(
    "body",
    [
        '{"x": 1, "x": 2}',
        '{"value": 1.000}',
        '{"value": NaN}',
        '{"value": Infinity}',
        "{not JSON}",
        '{"x":1}',
        "SELECT  1;",
        "<untrusted_source> preserve  spaces </untrusted_source>",
    ],
)
def test_noncanonical_or_plain_evidence_is_untouched(body):
    block = {"type": "tool_result", "content": body}
    assert json.loads(message_content([block])) == [block]


def test_learner_and_assistant_json_are_not_rewritten():
    body = '{"a": 1, "b": 2}'
    assert message_content(body) == body
    blocks = [{"type": "text", "text": body}, {"type": "tool_use", "input": {"sql": body}}]
    assert json.loads(message_content(blocks)) == blocks
