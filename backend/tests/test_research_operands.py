import pytest
from pydantic import ValidationError

from app.schemas.knowledge_authoring import (
    ResearchDiscussion,
    ResearchSectionDraft,
    ResearchTutorAnswer,
)


@pytest.mark.parametrize(
    "model,field", [(ResearchDiscussion, "answer_sentence"), (ResearchSectionDraft, "section")]
)
@pytest.mark.parametrize(
    "reason",
    [
        "because mixed-type operations are not automatically handled",
        "because mixed-type operations are not allowed",
        "because the '+' operator is not defined for mixed types",
        "because the '+' operator cannot handle different data types",
        "because Python does not support concatenating different data types",
    ],
)
def test_observed_false_operator_claim_requires_a_logged_repair(model, field, reason):
    with pytest.raises(ValidationError, match="Numeric int"):
        model.model_validate(
            {field: f"'Room ' + 2 raises TypeError {reason}.", "source_indices": [1]}
        )


@pytest.mark.parametrize(
    "text",
    [
        "String concatenation requires a string operand; use 'Room ' + str(2) for 'Room 2'.",
        "2 + 0.5 evaluates to 2.5; mixed numeric addition is supported.",
        "[1] + ['a'] concatenates lists; their elements may differ in type.",
        "'ab' * 3 repeats the string, producing 'ababab'.",
        "It is false that all mixed-type operations fail; int + float works.",
        "Deployment occurred later than the onset, so cannot explain that onset.",
    ],
)
def test_scoped_explanations_and_unrelated_answers_pass(text):
    assert ResearchSectionDraft(section=text, source_indices=[1]).section == text


def test_runtime_counterexamples_and_historical_answers_remain_intact():
    assert 2 + 0.5 == 2.5
    assert [1] + ["a"] == [1, "a"]
    assert "ab" * 3 == "ababab"
    with pytest.raises(TypeError):
        _ = "Room " + 2
    old = "Raises TypeError because mixed-type operations are not automatically handled."
    assert ResearchTutorAnswer(discussion=old).discussion == old


def test_negative_string_repetition_is_empty_not_value_error():
    assert "ab" * -2 == ""
    with pytest.raises(ValidationError, match="empty string"):
        ResearchSectionDraft(
            section="String repetition requires non-negative values; negative values raise a ValueError.",
            source_indices=[1],
        )
    ResearchSectionDraft(
        section="String repetition by a negative integer returns an empty string.",
        source_indices=[1],
    )


@pytest.mark.parametrize(
    "text",
    [
        "You likely confused repetition with an operation that raises ValueError.",
        "The original claim about ValueError likely confused this behavior with other operations.",
        "The result is empty because negative repetition truncates the string to zero length.",
        "This differs from list concatenation with negative counts, which may raise errors.",
    ],
)
def test_unsupported_mechanisms_and_mistake_origins_require_correction(text):
    with pytest.raises(ValidationError, match="origin of a learner"):
        ResearchSectionDraft(section=text, source_indices=[1])


def test_zero_repetitions_leave_original_sequence_unchanged():
    original = "xy"
    assert original * -2 == original * 0 == ""
    assert original == "xy"
    assert [1, 2] * -3 == []
    answer = "A negative count gives zero repetitions and an empty result; the original string stays unchanged."
    assert ResearchSectionDraft(section=answer, source_indices=[1]).section == answer


def test_negated_invented_mechanism_is_a_valid_correction():
    text = "Negative repetition does not truncate the original string; it returns an empty result."
    assert ResearchSectionDraft(section=text, source_indices=[1]).section == text


def test_negative_multiplier_does_not_truncate_original():
    with pytest.raises(ValidationError, match="origin of a learner"):
        ResearchSectionDraft(
            section="Negative multipliers truncate the original list.", source_indices=[1]
        )


def test_reassignment_does_not_mutate_original_string_object():
    original = "xy"
    name = original
    name = "z"
    assert original == "xy" and name == "z"
    with pytest.raises(ValidationError, match="Reassignment binds"):
        ResearchSectionDraft(
            section="String operations do not alter the original object unless explicitly reassigned.",
            source_indices=[1],
        )


def test_string_repetition_supports_both_operand_orders():
    assert "xy" * 2 == 2 * "xy" == "xyxy"
    with pytest.raises(ValidationError, match="both str"):
        ResearchSectionDraft(
            section="This operation requires the left operand to be a string and the right operand to be an integer.",
            source_indices=[1],
        )


@pytest.mark.parametrize(
    "text",
    [
        "String repetition with a negative count (s * -2) raises ValueError.",
        "It returns an empty list because negative repetition is not supported.",
    ],
)
def test_observed_contradictions_of_nonpositive_repetition(text):
    with pytest.raises(ValidationError, match="is supported"):
        ResearchSectionDraft(section=text, source_indices=[1])


@pytest.mark.parametrize(
    "text",
    [
        "A negative integer count does not raise ValueError for a string; the result is empty.",
        "A negative integer count doesn't raise ValueError for a string; the result is empty.",
        "A negative integer count never raises ValueError for string repetition.",
    ],
)
def test_negated_error_claims_remain_valid_corrections(text):
    assert ResearchSectionDraft(section=text, source_indices=[1]).section == text


def test_operand_word_order_cannot_hide_false_truncation():
    with pytest.raises(ValidationError, match="zero copies"):
        ResearchSectionDraft(
            section="List multiplication by a negative integer truncates the original list.",
            source_indices=[1],
        )


def test_negative_counts_are_valid_not_an_excluded_input_domain():
    with pytest.raises(ValidationError, match="accepts non-positive"):
        ResearchSectionDraft(
            section="The operation requires a non-negative integer; negative values produce an empty string.",
            source_indices=[1],
        )


def test_repetition_shares_inner_objects_and_later_mutation_is_distinct():
    xs = [[0]]
    ys = xs * 2
    assert ys[0] is ys[1] is xs[0]
    ys[0][0] = 1
    assert xs == [[1]] and ys == [[1], [1]]
