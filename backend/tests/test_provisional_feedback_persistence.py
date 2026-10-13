import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import assessment_executions, models, workspace_requests
from app.orchestrator import assessment_content, provisional_feedback
from app.schemas.grading import AttemptRequest


async def staged(db, learner):
    skill = models.SkillNode(domain="ai_ml", slug="provisional", title="Training split")
    session = models.Session(learner_id=learner.id, mode="steady", energy=3)
    db.add_all([skill, session])
    await db.flush()
    assessment = models.Assessment(
        skill_id=skill.id, kind="explain_back", item_json={"prompt": "Explain fitting."}
    )
    db.add(assessment)
    await db.commit()
    content = await assessment_content.snapshot(db, assessment.id, learner.id)
    body = AttemptRequest(
        session_id=session.id,
        assessment_id=assessment.id,
        answer="Train only",
        content_version=assessment_content.token(content),
    )
    payload = body.model_dump(mode="json")
    payload.pop("revision_of_attempt_id")
    claim = models.WorkspaceRequest(
        learner_id=learner.id,
        session_id=session.id,
        request_key="assessment:provisional",
        fingerprint=workspace_requests.request_fingerprint(payload),
    )
    db.add(claim)
    await db.commit()
    await assessment_executions.prepare(
        db,
        learner.id,
        claim.id,
        request_json=body.model_dump(mode="json"),
        content_fingerprint=assessment_content.recovery_fingerprint(content),
    )
    await assessment_executions.mark_inference_started(db, learner.id, claim.id)
    await assessment_executions.save_grade(
        db,
        learner.id,
        claim.id,
        grade_json={
            "version": 1,
            "level": "local",
            "result": {
                "criterion_results": [
                    {"criterion": "Train only", "passed": True, "evidence": "Train only"}
                ],
                "confidence": 0.9,
                "feedback": "Compare the held-out set.",
                "next_step": "Explain reuse.",
            },
        },
    )
    return claim.id, assessment.id


async def test_atomic_replay_is_advisory_without_learning_writes(db, learner):
    owner = learner.id
    claim, _ = await staged(db, learner)
    first = await provisional_feedback.persist_staged(db, owner, claim)
    second = await provisional_feedback.persist_staged(db, owner, claim)
    assert first == second
    assert (
        await provisional_feedback.get_owned(db, owner, first.feedback_id)
    ).answer == "Train only"
    assert await db.scalar(select(func.count()).select_from(models.ProvisionalFeedback)) == 1
    for table in (
        models.AssessmentAttempt,
        models.CompetencyEvidence,
        models.MemoryState,
        models.ReviewItem,
    ):
        assert await db.scalar(select(func.count()).select_from(table)) == 0
    events = list((await db.scalars(select(models.LearningEvent))).all())
    assert len(events) == 1
    assert events[0].verb == "provisional_feedback_saved"
    assert set(events[0].result_json) == {"feedback_len"}
    assert (await assessment_executions.get_owned(db, owner, claim)).phase == "completed"


async def test_changed_content_retains_staged_work(db, learner):
    owner = learner.id
    claim, aid = await staged(db, learner)
    assessment = await db.get(models.Assessment, aid)
    assessment.item_json = {"prompt": "Changed question"}
    await db.commit()
    with pytest.raises(AppError, match="earlier content"):
        await provisional_feedback.persist_staged(db, owner, claim)
    assert (await assessment_executions.get_owned(db, owner, claim)).phase == "grade_ready"
    assert await db.scalar(select(func.count()).select_from(models.ProvisionalFeedback)) == 0


async def test_failure_before_completion_rolls_back_record_and_receipt(db, learner, monkeypatch):
    owner = learner.id
    claim, _ = await staged(db, learner)
    original = assessment_executions.mark_completed

    async def fail(*args, **kwargs):
        raise RuntimeError("interrupted")

    monkeypatch.setattr(assessment_executions, "mark_completed", fail)
    with pytest.raises(RuntimeError, match="interrupted"):
        await provisional_feedback.persist_staged(db, owner, claim)
    assert await db.scalar(select(func.count()).select_from(models.ProvisionalFeedback)) == 0
    assert (await db.get(models.WorkspaceRequest, claim)).response_json is None
    assert await db.scalar(select(func.count()).select_from(models.LearningEvent)) == 0
    monkeypatch.setattr(assessment_executions, "mark_completed", original)
    await provisional_feedback.persist_staged(db, owner, claim)


async def test_foreign_claim_and_feedback_are_unavailable(db, learner):
    owner = learner.id
    claim, _ = await staged(db, learner)
    with pytest.raises(AppError):
        await provisional_feedback.persist_staged(db, "foreign", claim)
    result = await provisional_feedback.persist_staged(db, owner, claim)
    with pytest.raises(AppError):
        await provisional_feedback.get_owned(db, "foreign", result.feedback_id)


async def test_two_workers_return_one_record(db, learner, session_factory):
    import asyncio

    owner = learner.id
    claim, _ = await staged(db, learner)

    async def run():
        async with session_factory() as other:
            return await provisional_feedback.persist_staged(other, owner, claim)

    a, b = await asyncio.gather(run(), run())
    assert a.feedback_id == b.feedback_id
    assert await db.scalar(select(func.count()).select_from(models.ProvisionalFeedback)) == 1


@pytest.mark.parametrize("mutation", ["answer", "route"])
async def test_tampered_request_or_non_model_route_is_rejected(db, learner, mutation):
    owner = learner.id
    claim, _ = await staged(db, learner)
    execution = await assessment_executions.get_owned(db, owner, claim)
    if mutation == "answer":
        execution.request_json = {**execution.request_json, "answer": "different answer"}
    else:
        execution.grade_json = {**execution.grade_json, "level": "deterministic"}
    await db.commit()
    with pytest.raises(AppError):
        await provisional_feedback.persist_staged(db, owner, claim)
    assert await db.scalar(select(func.count()).select_from(models.ProvisionalFeedback)) == 0
