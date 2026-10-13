import pytest
from pydantic import ValidationError

from app.orchestrator.grader_transport import CriterionSnapshot, GraderResponse


def payload():
    return {
        "criterion_results": [
            {"criterion_id": "c2", "passed": False, "evidence": "absent"},
            {"criterion_id": "c1", "passed": True, "evidence": "training only"},
        ],
        "confidence": 0.8,
        "feedback": "One requirement missing.",
        "next_step": "Explain reuse.",
    }


def test_snapshot_maps_identity_not_order_and_retains_full_text():
    source = ["Fit: training only", "Reuse: same training parameter"]
    snapshot = CriterionSnapshot(tuple(source))
    source[0] = "changed"
    rows = snapshot.rows()
    rows[0]["criterion"] = "changed again"
    result = snapshot.resolve(GraderResponse.model_validate(payload()))
    assert [c.criterion for c in result.criterion_results] == [
        "Fit: training only",
        "Reuse: same training parameter",
    ]
    assert [c.passed for c in result.criterion_results] == [True, False]
    assert result.score == 0.5


@pytest.mark.parametrize("failure", ["missing", "duplicate", "unknown", "empty", "blank"])
def test_invalid_correspondence_rejected(failure):
    data = payload()
    rows = data["criterion_results"]
    if failure == "missing":
        rows.pop()
    elif failure == "blank":
        rows[0]["evidence"] = " \n "
    else:
        rows[0]["criterion_id"] = {"duplicate": "c1", "unknown": "c3", "empty": ""}[failure]
    with pytest.raises(ValueError):
        CriterionSnapshot(("A", "B")).resolve(GraderResponse.model_validate(data))


@pytest.mark.parametrize("value", ["true", "false", 1, 0, None])
def test_boolean_coercion_rejected(value):
    data = payload()
    data["criterion_results"][0]["passed"] = value
    with pytest.raises(ValidationError):
        GraderResponse.model_validate(data)


@pytest.mark.parametrize("nested", [True, False])
def test_extra_fields_rejected(nested):
    data = payload()
    target = data["criterion_results"][0] if nested else data
    target["criterion"] = "invented identity"
    with pytest.raises(ValidationError):
        GraderResponse.model_validate(data)


@pytest.mark.parametrize("criteria", [(), ("",), ("A", " a ")])
def test_invalid_rubric_rejected(criteria):
    with pytest.raises(ValueError):
        CriterionSnapshot(criteria)
