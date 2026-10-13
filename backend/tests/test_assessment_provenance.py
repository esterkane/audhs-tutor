"""Capture known facts atomically without inferring attainment or independence."""

import pytest
from pydantic import ValidationError

from app.db.models import Assessment
from app.schemas.assessment_provenance import AssessmentProvenance
from tests.test_assessment_revisions import original


async def test_new_attempt_keeps_versioned_facts_after_content_changes(client, db):
    root, _ = await original(client, db)
    assert root.deterministic_result_json is not None
    recorded = root.deterministic_result_json["evidence_provenance"]
    facts = AssessmentProvenance.model_validate(recorded)
    assert facts.schema_version == 1
    assert facts.task_kind == "mcq"
    assert facts.content_fingerprint == root.content_fingerprint
    assert facts.reported_hint_count == root.hint_count
    assert facts.grading_method == root.grader_route
    assert facts.revision_of_attempt_id is None
    assert facts.independence == "not_verified"
    assert facts.external_help == "unknown"
    assert facts.full_solution_exposure == "not_recorded"
    assert facts.qualification == "not_evaluated"
    assessment = await db.get(Assessment, root.assessment_id)
    assert assessment is not None
    assessment.item_json = {**assessment.item_json, "question": "Changed later"}
    await db.commit()
    await db.refresh(root)
    assert root.deterministic_result_json["evidence_provenance"] == recorded


@pytest.mark.parametrize(
    "field,value",
    [
        ("independence", "verified"),
        ("external_help", "none"),
        ("qualification", "passed"),
    ],
)
def test_snapshot_does_not_accept_inferred_attainment(field, value):
    data = dict(
        task_kind="code",
        content_fingerprint="fingerprint",
        rubric_version=None,
        grading_method="deterministic:client-pyodide",
        reported_hint_count=0,
        revision_of_attempt_id=None,
    )
    data[field] = value
    with pytest.raises(ValidationError):
        AssessmentProvenance.model_validate(data)


async def test_negative_client_report_does_not_strand_application_or_replay(client, db):
    from app.db.models import AssessmentAttempt
    from tests.test_assessment_requests import HEADERS, prepare

    body = await prepare(client, db)
    body["hint_count"] = -1
    first = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert first.status_code == 200, first.text
    root = await db.get(AssessmentAttempt, first.json()["attempt_id"])
    facts = root.deterministic_result_json["evidence_provenance"]
    assert facts["reported_hint_count"] == -1
    assert facts["qualification"] == "not_evaluated"
    replay = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert replay.status_code == 200
    assert replay.json()["attempt_id"] == root.id


async def test_local_model_result_stays_advisory_without_trusting_model_extras(
    client, db, monkeypatch
):
    from app.db.models import ProvisionalFeedback
    from app.orchestrator.grader import Grader, versioned_view
    from app.schemas.grading import GradeResult
    from tests.test_assessment_requests import HEADERS, prepare

    body = await prepare(client, db)
    assessment = await db.get(Assessment, body["assessment_id"])
    assessment.kind = "explain_back"
    assessment.item_json = {"prompt": "Explain how division compares quantities."}
    await db.commit()
    body["content_version"] = (await versioned_view(db, assessment)).content_version

    async def model_grade(*args, **kwargs):
        return GradeResult.model_validate(
            {
                "criterion_results": [{"criterion": "Explains comparison", "passed": True}],
                "confidence": 1,
                "feedback": "Synthetic feedback",
                "next_step": "",
                "evidence_provenance": {"independence": "verified"},
            }
        ), "local"

    monkeypatch.setattr(Grader, "_llm_grade", model_grade)
    response = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert response.status_code == 200, response.text
    saved = await db.get(ProvisionalFeedback, response.json()["feedback_id"])
    assert saved.policy_version == "model-feedback.v1"
    assert saved.model_output_json["level"] == "local"
    assert "evidence_provenance" not in saved.model_output_json["result"]
    assert "score" not in response.json()


async def test_review_binding_is_retained_without_awarding_evidence(client, db, monkeypatch):
    from app.db.models import AssessmentRubric, ProvisionalFeedback, Session
    from app.kernel import task_reviews
    from app.orchestrator.grader import Grader, versioned_view
    from app.schemas.grading import GradeResult
    from tests.test_assessment_requests import HEADERS, prepare
    from tests.test_task_reviews import command

    body = await prepare(client, db)
    task = await db.get(Assessment, body["assessment_id"])
    session = await db.get(Session, body["session_id"])
    rubric = AssessmentRubric(criteria_json=[{"criterion": "Explains comparison"}], version=1)
    db.add(rubric)
    await db.flush()
    task.kind = "explain_back"
    task.item_json = {"prompt": "Explain comparison"}
    task.rubric_id = rubric.id
    await db.commit()
    review = await task_reviews.decide(
        db, session.learner_id, task.id, await command(db, session.learner_id, task.id)
    )
    await db.commit()
    body["content_version"] = (await versioned_view(db, task)).content_version

    async def model_grade(*args, **kwargs):
        return GradeResult.model_validate(
            {
                "criterion_results": [{"criterion": "Explains comparison", "passed": True}],
                "confidence": 1,
                "feedback": "Synthetic",
                "next_step": "",
            }
        ), "local"

    monkeypatch.setattr(Grader, "_llm_grade", model_grade)
    response = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert response.status_code == 200, response.text
    saved = await db.get(ProvisionalFeedback, response.json()["feedback_id"])
    assert saved.binding_json["task_review"]["review"]["receipt_id"] == review.id
    assert "score" not in response.json()
    replay = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert replay.json()["feedback_id"] == saved.id
