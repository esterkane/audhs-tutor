import pytest
from pydantic import ValidationError

from app.schemas.provisional_feedback import ProvisionalFeedbackResult


def payload():
    return dict(
        feedback_id="f1",
        assessment_id="a1",
        session_id="s1",
        skill_id="k1",
        content_version="v1",
        feedback="Explain which data fits the parameter.",
        next_step="Compare training and held-out data.",
        model_route="local",
        criterion_feedback=[
            dict(criterion="Fit on training data", observation="You mentioned both sets.")
        ],
    )


def test_roundtrip_keeps_explicit_advisory_outcome_and_binding():
    result = ProvisionalFeedbackResult.model_validate(payload())
    restored = ProvisionalFeedbackResult.model_validate_json(result.model_dump_json())
    assert restored == result
    assert restored.outcome == "provisional_feedback"
    assert restored.policy_version == "model-feedback.v1"


@pytest.mark.parametrize(
    "field", ["score", "correct", "mastery", "review", "calibration", "attempt_id"]
)
def test_assessed_fields_are_rejected(field):
    with pytest.raises(ValidationError):
        ProvisionalFeedbackResult.model_validate({**payload(), field: 0})


def test_criterion_pass_flags_are_not_advisory_observations():
    value = payload()
    value["criterion_feedback"][0]["passed"] = True
    with pytest.raises(ValidationError):
        ProvisionalFeedbackResult.model_validate(value)


@pytest.mark.parametrize(
    "field", ["feedback_id", "assessment_id", "session_id", "skill_id", "content_version"]
)
def test_binding_fields_are_required(field):
    value = payload()
    del value[field]
    with pytest.raises(ValidationError):
        ProvisionalFeedbackResult.model_validate(value)
