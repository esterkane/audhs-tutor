import pytest
from pydantic import ValidationError

from app.schemas.grading import rubric_grade_model


def result(criteria):
    return {
        "criterion_results": [
            {"criterion": c, "passed": True, "evidence": "training ages only"} for c in criteria
        ],
        "confidence": 0.9,
        "feedback": "Uses the training median.",
        "next_step": "Apply it to the held-out set.",
    }


def test_rejects_shortened_duplicate_missing_and_empty_evidence():
    criteria = ["Training-only fit: Use training ages only.", "Reuse: Do not refit."]
    model = rubric_grade_model(criteria)
    for names in [["Training-only fit", "Reuse"], [criteria[0], criteria[0]], criteria[:1]]:
        with pytest.raises(ValidationError, match="entire text"):
            model.model_validate(result(names))
    payload = result(criteria)
    payload["criterion_results"][0]["evidence"] = " "
    with pytest.raises(ValidationError, match="evidence"):
        model.model_validate(payload)


def test_accepts_full_criterion_identities_in_any_order():
    criteria = ["Training-only fit: Use training ages only.", "Reuse: Do not refit."]
    grade = rubric_grade_model(criteria).model_validate(result(criteria[::-1]))
    assert grade.score == 1
