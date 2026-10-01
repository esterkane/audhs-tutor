import json

import pytest
from pydantic import ValidationError

from app.evals.grounded_feedback import bound_feedback


def payload(quote: str) -> dict:
    return {
        "points": [
            {
                "learner_quote": quote,
                "finding": "needs_revision",
                "explanation": "Check the quotient.",
            }
        ],
        "next_step": "Compare the resulting proportions.",
        "followup_question": None,
    }


def test_rejects_substituted_correction_and_history_quote() -> None:
    schema = bound_feedback("30/50 = 0.9, so 90%.", socratic=False)
    result = schema.model_validate(payload("30/50 = 0.9"))
    assert result.points[0].learner_quote == "30/50 = 0.9"
    for quote in ("30/50 = 0.6", "30/50 = 0.9, so 90%. You passed.", "", " "):
        with pytest.raises(ValidationError):
            schema.model_validate(payload(quote))


def test_classes_keep_different_answers_isolated_without_putting_them_in_schema() -> None:
    first = bound_feedback("private answer one", socratic=True)
    second = bound_feedback("private answer two", socratic=False)
    assert "private answer one" not in json.dumps(first.model_json_schema())
    first.model_validate(payload("answer one"))
    with pytest.raises(ValidationError):
        second.model_validate(payload("answer one"))
    first.model_validate(payload("answer one"))


def test_explicit_feedback_rejects_optional_question_and_unknown_fields() -> None:
    explicit = bound_feedback("An answer", socratic=False)
    with pytest.raises(ValidationError):
        explicit.model_validate({**payload("answer"), "followup_question": "Which denominator?"})
    with pytest.raises(ValidationError):
        explicit.model_validate({**payload("answer"), "followup_question": ""})
    with pytest.raises(ValidationError):
        explicit.model_validate({**payload("answer"), "grade": 100})
    assert (
        bound_feedback("An answer", socratic=True)
        .model_validate({**payload("answer"), "followup_question": "Which denominator?"})
        .followup_question
    )


def test_exact_unicode_whitespace_not_normalized_and_no_semantic_truth_claim() -> None:
    schema = bound_feedback("I said: café  →  60%", socratic=False)
    result = schema.model_validate(payload("café  →  60%"))
    assert (
        result.points[0].finding == "needs_revision"
    )  # A valid quote does not validate the judgment.
    with pytest.raises(ValidationError):
        schema.model_validate(payload("café → 60%"))


def test_empty_oversized_or_duplicate_input_is_rejected() -> None:
    for answer in ("", " ", "a" * 8001):
        with pytest.raises(ValueError):
            bound_feedback(answer, socratic=False)
    data = payload("a")
    data["points"] *= 2
    with pytest.raises(ValidationError):
        bound_feedback("answer", socratic=False).model_validate(data)
