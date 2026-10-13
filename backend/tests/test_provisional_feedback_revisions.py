import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import models
from app.orchestrator import assessment_revisions, provisional_feedback
from tests.test_provisional_feedback_persistence import staged


async def test_revision_source_returns_owned_answer_without_learning_writes(client, db, learner):
    owner = learner.id
    claim, _ = await staged(db, learner)
    result = await provisional_feedback.persist_staged(db, owner, claim)
    response = await client.get(
        f"/api/assess/feedback/{result.feedback_id}/revision",
        params={"session_id": result.session_id},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["feedback_id"] == data["root_feedback_id"] == result.feedback_id
    assert data["answer"] == "Train only"
    assert data["item"]["question"] == "Explain fitting."
    assert data["item"]["content_version"]
    for table in (
        models.AssessmentAttempt,
        models.CompetencyEvidence,
        models.MemoryState,
        models.ReviewItem,
    ):
        assert await db.scalar(select(func.count()).select_from(table)) == 0


@pytest.mark.parametrize(
    "case", ["foreign", "wrong_session", "wrong_item", "changed", "ended", "missing"]
)
async def test_revision_root_rejects_mismatched_or_changed_work(db, learner, case):
    owner = learner.id
    claim, aid = await staged(db, learner)
    result = await provisional_feedback.persist_staged(db, owner, claim)
    args = dict(
        learner_id=owner,
        session_id=result.session_id,
        assessment_id=aid,
        root_feedback_id=result.feedback_id,
    )
    if case == "foreign":
        other_learner = models.LearnerProfile(display_name="Other")
        db.add(other_learner)
        await db.flush()
        other_session = models.Session(learner_id=other_learner.id, mode="steady", energy=3)
        db.add(other_session)
        await db.flush()
        args["learner_id"] = other_learner.id
        args["session_id"] = other_session.id
    elif case == "wrong_session":
        other = models.Session(learner_id=owner, mode="steady", energy=3)
        db.add(other)
        await db.flush()
        args["session_id"] = other.id
    elif case == "wrong_item":
        args["assessment_id"] = "wrong"
    elif case == "missing":
        args["root_feedback_id"] = "missing"
    elif case == "changed":
        item = await db.get(models.Assessment, aid)
        item.item_json = {"prompt": "Changed"}
    else:
        session = await db.get(models.Session, result.session_id)
        session.ended_at = "2026-10-13T00:00:00Z"
    await db.commit()
    with pytest.raises(AppError):
        await assessment_revisions.validate_provisional_root(db, **args)
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0


async def test_revision_submit_replay_and_repeat_keep_advisory_lineage(
    client, db, learner, fake_local
):
    from app.models_ai import registry

    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    claim, _ = await staged(db, learner)
    root = await provisional_feedback.persist_staged(db, learner.id, claim)
    fake_local.structured = {
        "criterion_results": [
            {"criterion": "Train only", "passed": True, "evidence": "Training ages only"}
        ],
        "confidence": 0.9,
        "feedback": "You identify the training set.",
        "next_step": "Explain reuse.",
    }
    source = (
        await client.get(
            f"/api/assess/feedback/{root.feedback_id}/revision",
            params={"session_id": root.session_id},
        )
    ).json()
    body = dict(
        session_id=root.session_id,
        assessment_id=root.assessment_id,
        content_version=source["item"]["content_version"],
        answer="Fit on training ages only.",
        revision_of_feedback_id=root.feedback_id,
    )
    headers = {"Idempotency-Key": "775d83ce-2d09-44a7-b173-000000000001"}
    response = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["outcome"] == "provisional_feedback"
    assert result["revision_of_feedback_id"] == root.feedback_id
    assert result["feedback_id"] != root.feedback_id
    calls = len(fake_local.calls)
    replay = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert replay.json() == result
    assert len(fake_local.calls) == calls
    revised = (
        await client.get(
            f"/api/assess/feedback/{result['feedback_id']}/revision",
            params={"session_id": root.session_id},
        )
    ).json()
    assert revised["root_feedback_id"] == root.feedback_id
    assert revised["answer"] == body["answer"]
    both = await client.post(
        "/api/assess/attempt", json={**body, "revision_of_attempt_id": "wrong"}
    )
    assert both.status_code == 422
    child_as_root = await client.post(
        "/api/assess/attempt", json={**body, "revision_of_feedback_id": result["feedback_id"]}
    )
    assert child_as_root.status_code == 409
    assert len(fake_local.calls) == calls
    without_key = await client.post("/api/assess/attempt", json=body)
    assert without_key.status_code == 200, without_key.text
    assert without_key.json()["outcome"] == "provisional_feedback"
    assert without_key.json()["revision_of_feedback_id"] == root.feedback_id
    for table in (
        models.AssessmentAttempt,
        models.CompetencyEvidence,
        models.MemoryState,
        models.ReviewItem,
    ):
        assert await db.scalar(select(func.count()).select_from(table)) == 0
