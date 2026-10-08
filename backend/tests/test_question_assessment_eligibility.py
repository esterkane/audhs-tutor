"""Suspension applies to new grading and pending recovery, not historical replay."""

from uuid import uuid4

from sqlalchemy import func, select

from app.db import models
from app.kernel import question_state
from app.schemas.question_state import QuestionTransitionIn
from tests.test_assessment_content_versions import KEY, prepare
from tests.test_assessment_finish_recovery import finish, stage_failed
from tests.test_assessment_prepared_continuation import staged, url


async def change(db, body, action="suspend", revision=0):
    session = await db.get(models.Session, body["session_id"])
    await question_state.transition(
        db,
        session.learner_id,
        body["assessment_id"],
        QuestionTransitionIn(request_id=uuid4(), action=action, expected_revision=revision),
    )
    await db.commit()


async def attempts(db):
    return await db.scalar(select(func.count()).select_from(models.AssessmentAttempt))


async def test_suspended_direct_access_and_new_claim_blocked(client, db, fake_local):
    body = await prepare(client, db)
    await change(db, body)
    shown = await client.get(
        "/api/assess/items/" + body["assessment_id"], params={"session_id": body["session_id"]}
    )
    assert shown.status_code == 409
    result = await client.post("/api/assess/attempt", json=body, headers={"Idempotency-Key": KEY})
    assert result.status_code == 409
    assert await attempts(db) == 0
    assert await db.scalar(select(func.count()).select_from(models.WorkspaceRequest)) == 0
    assert not fake_local.calls


async def test_restore_requires_fresh_question_token(client, db):
    body = await prepare(client, db)
    await change(db, body)
    await change(db, body, "restore", 1)
    result = await client.post("/api/assess/attempt", json=body)
    assert result.status_code == 409
    shown = await client.get(
        "/api/assess/items/" + body["assessment_id"], params={"session_id": body["session_id"]}
    )
    assert shown.status_code == 200
    body["content_version"] = shown.json()["content_version"]
    assert (await client.post("/api/assess/attempt", json=body)).status_code == 200


async def test_completed_assessment_replays_after_suspension(client, db):
    body = await prepare(client, db)
    headers = {"Idempotency-Key": KEY}
    first = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert first.status_code == 200
    await change(db, body)
    result = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert result.status_code == 200 and result.json() == first.json()
    assert await attempts(db) == 1


async def test_prepared_continuation_does_not_bypass_suspension(
    client, db, monkeypatch, fake_local
):
    body, _ = await staged(client, db, monkeypatch)
    await change(db, body)
    assert (await client.get(url(body))).json()["status"] == "unresolved"
    result = await client.post(url(body, "/continue"))
    assert result.status_code == 409
    assert await attempts(db) == 0 and not fake_local.calls


async def test_saved_grade_cannot_update_progress_after_suspension(
    client, db, monkeypatch, fake_local
):
    body = await stage_failed(client, db, monkeypatch)
    await change(db, body)
    result = await finish(client, body)
    assert result.status_code == 409
    assert await attempts(db) == 0 and not fake_local.calls
    execution = await db.scalar(select(models.AssessmentExecution))
    assert execution.phase == "grade_ready" and execution.grade_json is not None


async def test_direct_grader_cannot_bypass_status(client, db, fake_local):
    import pytest

    from app.core.errors import AppError
    from app.orchestrator.grader import Grader
    from app.schemas.grading import AttemptRequest

    body = await prepare(client, db)
    await change(db, body)
    body.pop("content_version")
    with pytest.raises(AppError, match="no longer available"):
        await Grader(db, None).grade(AttemptRequest(**body))
    assert await attempts(db) == 0 and not fake_local.calls


async def test_inference_time_suspend_and_restore_blocks_learning_commit(
    client, db, monkeypatch, session_factory
):
    from app.orchestrator.grader import Grader
    from app.schemas.grading import CriterionResult, GradeResult

    body = await prepare(client, db)
    a = await db.get(models.Assessment, body["assessment_id"])
    rubric = models.AssessmentRubric(
        criteria_json=[{"criterion": "Explain", "keywords": []}], version=1
    )
    db.add(rubric)
    await db.flush()
    a.kind, a.rubric_id, a.item_json = "explain_back", rubric.id, {"prompt": "Explain this"}
    await db.commit()
    shown = await client.get(
        "/api/assess/items/" + body["assessment_id"], params={"session_id": body["session_id"]}
    )
    body["content_version"] = shown.json()["content_version"]
    body["answer"] = "My explanation"

    async def changed(self, *args, **kwargs):
        self.execution.gateway_entered = True
        async with session_factory() as other:
            await change(other, body)
            await change(other, body, "restore", 1)
        return GradeResult(
            criterion_results=[CriterionResult(criterion="Explain", passed=True)],
            confidence=1,
            feedback="Synthetic",
            next_step="Continue",
        ), "local"

    monkeypatch.setattr(Grader, "_llm_grade", changed)
    result = await client.post("/api/assess/attempt", json=body, headers={"Idempotency-Key": KEY})
    assert result.status_code == 409, result.text
    assert result.json()["error"]["code"] == "assessment_content_changed_during_grading"
    assert await attempts(db) == 0
    assert await db.scalar(select(func.count()).select_from(models.CompetencyEvidence)) == 0
    execution = await db.scalar(select(models.AssessmentExecution))
    assert execution.phase == "grade_ready" and execution.grade_json is not None


async def test_snapshot_status_is_learner_scoped(client, db):
    from app.orchestrator import assessment_content

    body = await prepare(client, db)
    original = await assessment_content.snapshot(db, body["assessment_id"])
    other = models.LearnerProfile(display_name="Another learner")
    db.add(other)
    await db.commit()
    await change(db, body)
    unaffected = await assessment_content.snapshot(db, body["assessment_id"], other.id)
    assert unaffected == original
    assessment_content.require_eligible(unaffected)
