"""Policy integration with synthetic model results, not accuracy evidence."""

import pytest
from sqlalchemy import func, select

from app.db import models
from app.orchestrator import assessment_content
from app.orchestrator.grader import Grader
from app.schemas.grading import AttemptRequest, GradeResult
from tests.test_provisional_feedback_persistence import staged


@pytest.mark.parametrize("level", ["local", "hosted"])
async def test_reusable_direct_grader_gets_separate_advisory_claims(
    db, learner, monkeypatch, level
):
    claim, aid = await staged(db, learner)
    initial_claim = await db.get(models.WorkspaceRequest, claim)
    request = AttemptRequest(session_id=initial_claim.session_id, assessment_id=aid, answer="First")

    async def synthetic(*args, **kwargs):
        return GradeResult(
            criterion_results=[], confidence=1, feedback="Advisory", next_step="Explain"
        ), level

    monkeypatch.setattr(Grader, "_llm_grade", synthetic)
    grader = Grader(db, None)
    first = await grader.grade(request)
    second = await grader.grade(request.model_copy(update={"answer": "Second"}))
    assert first.outcome == second.outcome == "provisional_feedback"
    assert first.feedback_id != second.feedback_id
    assert grader.request_claim_id is None
    rows = list((await db.scalars(select(models.ProvisionalFeedback))).all())
    assert {row.answer for row in rows} == {"First", "Second"}
    assert len({row.claim_id for row in rows}) == 2
    for table in (
        models.AssessmentAttempt,
        models.CompetencyEvidence,
        models.MemoryState,
        models.ReviewItem,
    ):
        assert await db.scalar(select(func.count()).select_from(table)) == 0


async def test_historical_assessed_revision_becomes_advisory(client, db, learner, monkeypatch):
    claim, aid = await staged(db, learner)
    original_claim = await db.get(models.WorkspaceRequest, claim)
    content = await assessment_content.snapshot(db, aid, learner.id)
    old = models.AssessmentAttempt(
        learner_id=learner.id,
        session_id=original_claim.session_id,
        assessment_id=aid,
        content_fingerprint=assessment_content.recovery_fingerprint(content),
        answer="Historical answer",
        grader_route="local",
        correct=True,
    )
    db.add(old)
    await db.commit()

    async def synthetic(*args, **kwargs):
        return GradeResult(
            criterion_results=[], confidence=1, feedback="Advisory", next_step="Explain"
        ), "local"

    monkeypatch.setattr(Grader, "_llm_grade", synthetic)
    response = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": old.session_id,
            "assessment_id": aid,
            "content_version": assessment_content.token(content),
            "answer": "Revised answer",
            "revision_of_attempt_id": old.id,
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["outcome"] == "provisional_feedback"
    assert result["previous_assessed_attempt_id"] == old.id
    assert result["revision_of_feedback_id"] is None
    assert "score" not in result
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 1
    await db.refresh(old)
    assert old.answer == "Historical answer" and old.correct is True
    for table in (models.CompetencyEvidence, models.MemoryState, models.ReviewItem):
        assert await db.scalar(select(func.count()).select_from(table)) == 0


async def test_completed_historical_model_outcome_replays_unchanged(client, db, monkeypatch):
    from tests.test_assessment_requests import prepare

    body = await prepare(client, db)
    item = await db.get(models.Assessment, body["assessment_id"])
    item.kind = "explain_back"
    item.item_json = {"prompt": "Explain fitting"}
    await db.commit()
    body["content_version"] = assessment_content.token(
        await assessment_content.snapshot(db, item.id)
    )
    body["answer"] = "Historical response"

    async def synthetic(*args, **kwargs):
        return GradeResult(
            criterion_results=[], confidence=1, feedback="Historical feedback", next_step=""
        ), "local"

    async def old_application(self, *args, **kwargs):
        # Seed a pre-policy receipt through the former assessed writer.
        return await self._apply_result(*args, **kwargs)

    headers = {"Idempotency-Key": "37ee7cb9-f26e-4263-88ec-000000000001"}
    with monkeypatch.context() as old:
        old.setattr(Grader, "_llm_grade", synthetic)
        old.setattr(Grader, "apply_result", old_application)
        historical = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert historical.status_code == 200, historical.text
    assert "score" in historical.json()

    async def never_grade(*args, **kwargs):
        raise AssertionError("Historical replay must not grade")

    monkeypatch.setattr(Grader, "grade", never_grade)
    replay = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert replay.status_code == 200
    assert replay.json() == historical.json()
    assert await db.scalar(select(func.count()).select_from(models.ProvisionalFeedback)) == 0
