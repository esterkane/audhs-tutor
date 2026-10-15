"""Exact reference contracts; passing does not prove semantic support or ownership."""

import pytest
from pydantic import ValidationError

from app.orchestrator.answer_check_binding import text_hash
from app.orchestrator.ask_context_binding import ContextInput, validate_references
from app.schemas.ask_context_proposals import ContextProposal


def proposal(text="Use training only", **reference):
    return ContextProposal.model_validate(
        {
            "changes": [
                {
                    "field": "notes",
                    "value": "Retain the rule",
                    "rationale": "Keep task context",
                    "references": [
                        {
                            "input_id": "S1",
                            "text_hash": text_hash(text),
                            "start": 0,
                            "end": len(text),
                            **reference,
                        }
                    ],
                }
            ]
        }
    )


def inputs(text="Use training only"):
    return {"S1": ContextInput(text, "selected_source", "version-one", text_hash(text))}


def test_binding_is_detached_and_unicode_ranges_use_original_text():
    text = "Ä 😀 <example>"
    original = proposal(text, start=2, end=3)
    checked = validate_references(original, inputs(text))
    original.changes[0].value = "Changed after validation"
    assert checked.changes[0].value == "Retain the rule"
    assert (
        text[checked.changes[0].references[0].start : checked.changes[0].references[0].end] == "😀"
    )


@pytest.mark.parametrize("override", [{"input_id": "other"}, {"text_hash": "0" * 64}, {"end": 100}])
def test_missing_changed_and_out_of_range_references_fail(override):
    with pytest.raises(ValueError):
        validate_references(proposal(**override), inputs())


def test_whitespace_and_oversized_context_fail():
    with pytest.raises(ValueError, match="whitespace"):
        validate_references(proposal("   "), inputs("   "))
    with pytest.raises(ValueError, match="bound"):
        validate_references(proposal(), inputs("x" * 24001))


@pytest.mark.parametrize(
    "override", [{"start": True}, {"start": "0"}, {"start": 2, "end": 1}, {"verified": True}]
)
def test_bad_reference_types_ranges_and_authority_are_rejected(override):
    with pytest.raises(ValidationError):
        proposal(**override)


def test_field_limits_duplicates_and_no_change_proposal():
    assert validate_references(ContextProposal(changes=[]), inputs()).changes == []
    raw = proposal().model_dump()
    raw["changes"][0]["field"] = "task"
    raw["changes"][0]["value"] = "x" * 501
    with pytest.raises(ValidationError):
        ContextProposal.model_validate(raw)
    raw = proposal().model_dump()
    raw["changes"].append(raw["changes"][0])
    with pytest.raises(ValidationError):
        ContextProposal.model_validate(raw)
    raw = proposal().model_dump()
    raw["changes"][0]["references"] *= 2
    with pytest.raises(ValidationError):
        ContextProposal.model_validate(raw)


def test_valid_span_does_not_certify_meaning_or_add_permissions():
    value = proposal()
    value.changes[0].value = "Fit on held-out data instead"
    checked = validate_references(value, inputs())
    assert checked.changes[0].value == value.changes[0].value
    assert "verified" not in checked.model_dump()
    assert "hosted_allowed" not in checked.model_dump()


@pytest.mark.parametrize("version", [True, 1.0, "1", 2])
def test_version_is_not_coerced(version):
    with pytest.raises(ValidationError):
        ContextProposal.model_validate({"version": version, "changes": []})
