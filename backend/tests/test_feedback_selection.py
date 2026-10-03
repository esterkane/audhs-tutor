import json

import pytest
from pydantic import ValidationError

from app.orchestrator.feedback_render import render_feedback
from app.schemas.feedback_selection import bound_selection, build_passages, to_quoted


def payload(ids, followup=None):
    return {
        "points": [
            {
                "passage_id": value,
                "finding": "needs_revision",
                "explanation": "Check the supplied claim.",
            }
            for value in ids
        ],
        "next_step": "Compare the quantities.",
        "followup_question": followup,
    }


@pytest.mark.parametrize(
    "answer",
    [
        "  αβ😀\tmeaning\n" * 450,
        "界" * 8000,
        "one " * 150,
        " x ",
        "a" * 399 + " b",
        "a" * 400 + "b",
    ],
)
def test_spans_exact_bounded_and_cover_nonwhitespace(answer):
    passages = build_passages(answer)
    assert passages == build_passages(answer)
    covered = set()
    for item in passages:
        assert item["text"] == answer[item["start"] : item["end"]]
        assert 0 < len(item["text"]) <= 400
        assert item["text"].strip()
        covered.update(range(item["start"], item["end"]))
    assert all(i in covered for i, char in enumerate(answer) if not char.isspace())
    assert len({p["id"] for p in passages}) == len(passages)


@pytest.mark.parametrize("answer", ["", " \n\t", "a" * 8001])
def test_invalid_answers_rejected_without_echo(answer):
    with pytest.raises(ValueError, match="nonempty bounded"):
        build_passages(answer)


def test_request_scope_and_exact_render_conversion():
    answer = "  Original_😀 \\ text <tag> " + "more " * 90
    passages = build_passages(answer)
    schema = bound_selection(answer, socratic=False)
    selection = schema.model_validate(payload([passages[0]["id"]]))
    quoted = to_quoted(answer, selection, socratic=False)
    assert quoted.points[0].learner_quote == passages[0]["text"]
    assert quoted.points[0].learner_quote in answer
    assert "You wrote:" in render_feedback(quoted)
    other = bound_selection(answer + "changed", socratic=False)
    with pytest.raises(ValidationError) as error:
        other.model_validate(selection.model_dump())
    assert error.value.errors(include_input=False)[0]["type"] == "selection_unknown"
    assert "Original_" not in json.dumps(schema.model_json_schema())


@pytest.mark.parametrize("kind", ["unknown", "duplicate", "followup"])
def test_typed_reasons(kind):
    answer = "x" * 400 + "x" * 400
    ids = [item["id"] for item in build_passages(answer)]
    schema = bound_selection(answer, socratic=False)
    body = payload(
        ["not-an-id"] if kind == "unknown" else ids if kind == "duplicate" else ids[:1],
        "Why?" if kind == "followup" else None,
    )
    with pytest.raises(ValidationError) as error:
        schema.model_validate(body)
    assert (
        error.value.errors(include_input=False)[0]["type"]
        == {
            "unknown": "selection_unknown",
            "duplicate": "quote_duplicate",
            "followup": "explicit_followup_forbidden",
        }[kind]
    )


def test_point_cap_and_socratic_question():
    schema = bound_selection("one passage", socratic=True)
    id_ = build_passages("one passage")[0]["id"]
    assert schema.model_validate(payload([id_], "Why?")).followup_question == "Why?"
    with pytest.raises(ValidationError):
        schema.model_validate(payload([id_, id_]))
    assert schema.model_json_schema()["properties"]["points"]["maxItems"] == 1
