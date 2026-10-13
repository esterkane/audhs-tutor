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
    rubric = models.AssessmentRubric(version=1, criteria_json=[{"criterion": "Train only"}])
    db.add(rubric)
    await db.flush()
    assessment = models.Assessment(
        rubric_id=rubric.id,
        skill_id=skill.id,
        kind="explain_back",
        item_json={"prompt": "Explain fitting."},
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
    payload = body.identity_payload()
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
    assert await db.scalar(select(func.count()).select_from(models.TutorAnswer)) == 0
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


async def test_completed_provisional_response_replays_through_http(client, db, learner):
    owner = learner.id
    claim, _ = await staged(db, learner)
    request_id = "9eb408fa-bf60-49bb-80e2-d0c1f293efba"
    row = await db.get(models.WorkspaceRequest, claim)
    row.request_key = f"assessment:{request_id}"
    session_id = row.session_id
    await db.commit()
    result = await provisional_feedback.persist_staged(db, owner, claim)
    response = await client.get(
        f"/api/assess/requests/{request_id}", params={"session_id": session_id}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["result"] == result.model_dump(mode="json")
    assert not ({"score", "correct", "mastery", "review"} & set(body["result"]))


async def test_advisory_answer_allows_continuation_only_for_matching_block(db, learner):
    from app.db.base import utcnow_iso
    from app.kernel.blocks import _answered_since

    owner = learner.id
    claim, aid = await staged(db, learner)
    request = await db.get(models.WorkspaceRequest, claim)
    session = await db.get(models.Session, request.session_id)
    assessment = await db.get(models.Assessment, aid)
    checkpoint = {"block_started_at": utcnow_iso(), "skill_id": assessment.skill_id}
    assert not await _answered_since(db, session, checkpoint)
    await provisional_feedback.persist_staged(db, owner, claim)
    assert await _answered_since(db, session, checkpoint)
    assert not await _answered_since(db, session, {**checkpoint, "skill_id": "another"})


async def test_advisory_history_context_is_exact_and_replay_deduplicated(db, learner):
    from app.orchestrator.assessment_help import load_context

    owner = learner.id
    claim, aid = await staged(db, learner)
    first = await provisional_feedback.persist_staged(db, owner, claim)
    second = await provisional_feedback.persist_staged(db, owner, claim)
    assert first.answer_id == second.answer_id
    assert await db.scalar(select(func.count()).select_from(models.TutorAnswer)) == 1
    saved = await db.get(models.TutorAnswer, first.answer_id)
    assert "not an assessed result" in saved.text
    assert "assessment_attempt_id" not in saved.metadata_json
    item = await db.get(models.Assessment, aid)
    item.item_json = {"prompt": "Edited live question"}
    await db.commit()
    context = await load_context(
        db,
        answer_id=first.answer_id,
        learner_id=owner,
        session_id=first.session_id,
        skill_id=first.skill_id,
    )
    assert context["question"]["question"] == "Explain fitting."
    assert context["submitted_answer"] == "Train only"
    assert context["recorded_result"]["outcome"] == "provisional_feedback"
    assert "not an assessed result" in context["solution_status"]
    for field in ("learner_id", "session_id", "skill_id"):
        args = dict(
            answer_id=first.answer_id,
            learner_id=owner,
            session_id=first.session_id,
            skill_id=first.skill_id,
        )
        args[field] = "foreign"
        with pytest.raises(AppError):
            await load_context(db, **args)
    saved.request_json = {**saved.request_json, "learner_answer": "Forged answer"}
    await db.flush()
    with pytest.raises(AppError, match="could not be verified"):
        await load_context(
            db,
            answer_id=first.answer_id,
            learner_id=owner,
            session_id=first.session_id,
            skill_id=first.skill_id,
        )


async def test_tutor_help_receives_advisory_snapshot_without_grade_claims(
    client, db, learner, fake_local
):
    from app.models_ai import registry

    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    owner = learner.id
    claim, _ = await staged(db, learner)
    result = await provisional_feedback.persist_staged(db, owner, claim)
    fake_local.calls.clear()
    response = await client.post(
        "/api/tutor/turn",
        json={
            "session_id": result.session_id,
            "skill_id": result.skill_id,
            "assessment_answer_id": result.answer_id,
            "action": "explain",
            "text": "Explain the difficult part",
        },
    )
    assert response.status_code == 200, response.text
    prompt = "\n".join(message.content for call in fake_local.calls for message in call.messages)
    assert "Provisional model feedback only, not an assessed result" in prompt
    assert "Explain fitting." in prompt
    assert "Train only" in prompt
    assert "criterion_feedback" in prompt
    assert "criterion_results" not in prompt
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0
