from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from app.core.content_versions import token
from app.core.errors import AppError
from app.db.models import (
    Assessment,
    AssessmentRubric,
    AssessmentTaskReview,
    CompetencyEvidence,
    LearnerProfile,
    MemoryState,
    SkillNode,
)
from app.kernel import task_reviews
from app.schemas.task_reviews import TaskReviewCommand


async def setup_task(db):
    skill = SkillNode(
        slug=str(uuid4()), title="Explain an example", domain="test", description="Explain why"
    )
    rubric = AssessmentRubric(criteria_json=[{"criterion": "Give a causal explanation"}], version=1)
    db.add_all([skill, rubric])
    await db.flush()
    task = Assessment(
        skill_id=skill.id, kind="explain_back", rubric_id=rubric.id, item_json={"prompt": "Why?"}
    )
    db.add(task)
    await db.commit()
    return task, rubric, skill


async def command(db, learner_id, task_id, **overrides):
    content = await task_reviews.snapshot(db, learner_id, task_id)
    return TaskReviewCommand.model_validate(
        {
            "request_id": str(uuid4()),
            "expected_revision": 0,
            "content_version": token(content),
            "decision": "approve",
            "facet": "explanation",
            "confirmed": True,
            **overrides,
        }
    )


async def test_review_replay_revoke_and_no_learning_evidence(db, learner):
    task, _, _ = await setup_task(db)
    body = await command(db, learner.id, task.id)
    result = await task_reviews.decide(db, learner.id, task.id, body)
    await db.commit()
    assert result.revision == 1 and result.policy_version == "task-review-v1"
    assert await task_reviews.decide(db, learner.id, task.id, body) == result
    assert await db.scalar(select(func.count()).select_from(AssessmentTaskReview)) == 1
    assert await db.scalar(select(func.count()).select_from(CompetencyEvidence)) == 0
    assert await db.scalar(select(func.count()).select_from(MemoryState)) == 0
    revoke = await command(db, learner.id, task.id, expected_revision=1, decision="revoke")
    revoked = await task_reviews.decide(db, learner.id, task.id, revoke)
    await db.commit()
    assert revoked.revision == 2 and revoked.decision == "revoke"
    assert (await db.get(AssessmentTaskReview, result.id)).decision == "approve"
    assert await task_reviews.decide(db, learner.id, task.id, body) == result
    assert (await task_reviews.latest(db, learner.id, task.id)).id == revoked.id


@pytest.mark.parametrize("target", ["task", "rubric", "objective"])
async def test_review_requires_exact_content(db, learner, target):
    task, rubric, skill = await setup_task(db)
    body = await command(db, learner.id, task.id)
    if target == "task":
        task.item_json = {"prompt": "Changed question"}
    elif target == "rubric":
        rubric.criteria_json = [{"criterion": "Changed criterion"}]
    else:
        skill.description = "Changed objective"
    await db.commit()
    with pytest.raises(AppError, match="changed"):
        await task_reviews.decide(db, learner.id, task.id, body)
    await db.rollback()
    assert await db.scalar(select(func.count()).select_from(AssessmentTaskReview)) == 0


async def test_review_request_and_revision_conflicts(db, learner):
    learner_id = learner.id
    task, _, _ = await setup_task(db)
    task_id = task.id
    body = await command(db, learner_id, task_id)
    await task_reviews.decide(db, learner_id, task_id, body)
    await db.commit()
    with pytest.raises(AppError):
        await task_reviews.decide(
            db, learner_id, task_id, body.model_copy(update={"facet": "application"})
        )
    await db.rollback()
    stale = await command(db, learner_id, task_id)
    with pytest.raises(AppError):
        await task_reviews.decide(db, learner_id, task_id, stale)
    await db.rollback()
    assert await db.scalar(select(func.count()).select_from(AssessmentTaskReview)) == 1


async def test_review_is_owner_scoped_and_rollback_safe(db, learner):
    learner_id = learner.id
    task, _, _ = await setup_task(db)
    task_id = task.id
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    other_id = other.id
    body = await command(db, learner_id, task_id)
    receipt = await task_reviews.decide(db, learner_id, task_id, body)
    await db.rollback()
    assert await db.get(AssessmentTaskReview, receipt.id) is None
    task_id = receipt.assessment_id
    task = await db.get(Assessment, task_id)
    # Deliberate fixture corruption to retain defensive access checks.
    await db.execute(text("DROP TRIGGER assessment_owner_immutable"))
    task.owner_learner_id = other_id
    await db.commit()
    with pytest.raises(AppError):
        await task_reviews.decide(db, learner_id, task_id, body)
    await db.rollback()
    assert await task_reviews.latest(db, other_id, task_id) is None


@pytest.mark.parametrize(
    "change", ["confirmation", "empty_rubric", "duplicate_rubric", "code", "revoke_without_review"]
)
async def test_review_refuses_unsupported_or_unconfirmed_decision(db, learner, change):
    task, rubric, _ = await setup_task(db)
    if change == "empty_rubric":
        rubric.criteria_json = []
    elif change == "duplicate_rubric":
        rubric.criteria_json = [{"criterion": "Same"}, {"criterion": "same"}]
    elif change == "code":
        task.kind = "code"
    await db.commit()
    body = await command(
        db,
        learner.id,
        task.id,
        confirmed=change != "confirmation",
        decision="revoke" if change == "revoke_without_review" else "approve",
    )
    with pytest.raises(AppError):
        await task_reviews.decide(db, learner.id, task.id, body)
    await db.rollback()
    assert await db.scalar(select(func.count()).select_from(AssessmentTaskReview)) == 0


async def test_review_export_and_wipe_preserve_other_owner(db, learner, db_path):
    from app.db.portability import export_learner, wipe_learner
    from app.db.session import sync_connect

    task, _, _ = await setup_task(db)
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    owner_id, other_id = learner.id, other.id
    for owner in (owner_id, other_id):
        body = await command(db, owner, task.id)
        await task_reviews.decide(db, owner, task.id, body)
        await db.commit()
    conn = sync_connect(f"sqlite:///{db_path}")
    try:
        rows = export_learner(conn, owner_id)["assessment_task_review"]
        assert len(rows) == 1 and rows[0]["decision"] == "approve"
        assert wipe_learner(conn, owner_id)["assessment_task_review"] == 1
        assert len(export_learner(conn, other_id)["assessment_task_review"]) == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()


async def test_parallel_replay_creates_one_review(db, learner):
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    task, _, _ = await setup_task(db)
    learner_id, task_id = learner.id, task.id
    body = await command(db, learner_id, task_id)
    await db.commit()
    sessions = async_sessionmaker(db.bind, expire_on_commit=False)

    async def perform():
        async with sessions() as connection:
            result = await task_reviews.decide(connection, learner_id, task_id, body)
            await connection.commit()
            return result

    first, second = await asyncio.gather(perform(), perform())
    assert first == second
    assert await db.scalar(select(func.count()).select_from(AssessmentTaskReview)) == 1


async def test_unicode_preview_is_controlled_conflict(db, learner):
    task, _, _ = await setup_task(db)
    body = await command(db, learner.id, task.id, content_version="é")
    with pytest.raises(AppError, match="changed"):
        await task_reviews.decide(db, learner.id, task.id, body)
    await db.rollback()


async def test_review_preserves_exact_historical_content(db, learner):
    task, rubric, skill = await setup_task(db)
    original = await task_reviews.snapshot(db, learner.id, task.id)
    body = await command(db, learner.id, task.id)
    result = await task_reviews.decide(db, learner.id, task.id, body)
    await db.commit()
    task.item_json = {"prompt": "New task"}
    rubric.criteria_json = [{"criterion": "New rubric"}]
    skill.description = "New objective"
    await db.commit()
    saved = await db.get(AssessmentTaskReview, result.id, populate_existing=True)
    assert saved.content_json == original
    assert saved.content_fingerprint == task_reviews.fingerprint(original)


async def test_parallel_distinct_commands_conflict(db, learner):
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    task, _, _ = await setup_task(db)
    learner_id, task_id = learner.id, task.id
    bodies = [await command(db, learner_id, task_id) for _ in range(2)]
    await db.commit()
    sessions = async_sessionmaker(db.bind, expire_on_commit=False)

    async def perform(body):
        async with sessions() as connection:
            try:
                result = await task_reviews.decide(connection, learner_id, task_id, body)
                await connection.commit()
                return result
            except AppError:
                await connection.rollback()
                return None

    results = await asyncio.gather(*(perform(body) for body in bodies))
    assert sum(result is not None for result in results) == 1
    assert await db.scalar(select(func.count()).select_from(AssessmentTaskReview)) == 1


async def test_suspend_restore_invalidates_preview(db, learner):
    from app.kernel import question_state
    from app.schemas.question_state import QuestionTransitionIn

    task, _, _ = await setup_task(db)
    learner_id, task_id = learner.id, task.id
    original = await command(db, learner_id, task_id)
    for revision, action in enumerate(("suspend", "restore")):
        await question_state.transition(
            db,
            learner_id,
            task_id,
            QuestionTransitionIn(request_id=uuid4(), expected_revision=revision, action=action),
        )
        await db.commit()
        with pytest.raises(AppError, match="changed"):
            await task_reviews.decide(db, learner_id, task_id, original)
        await db.rollback()
        if action == "suspend":
            suspended = await command(db, learner_id, task_id)
            with pytest.raises(AppError, match="active"):
                await task_reviews.decide(db, learner_id, task_id, suspended)
            await db.rollback()
    fresh = await command(db, learner_id, task_id)
    assert (await task_reviews.decide(db, learner_id, task_id, fresh)).decision == "approve"


async def test_preview_distinguishes_approval_from_changed_content(db, learner):
    task, rubric, _ = await setup_task(db)
    before = await task_reviews.preview(db, learner.id, task.id)
    assert before.reviewable and not before.approval_matches_content
    assert before.current_review is None
    body = await command(db, learner.id, task.id)
    approved = await task_reviews.decide(db, learner.id, task.id, body)
    await db.commit()
    current = await task_reviews.preview(db, learner.id, task.id)
    assert current.approval_matches_content and current.current_review == approved
    rubric.criteria_json = [{"criterion": "Revised criterion"}]
    await db.commit()
    changed = await task_reviews.preview(db, learner.id, task.id)
    assert changed.current_review == approved
    assert not changed.approval_matches_content
    assert changed.content_version != before.content_version


async def test_unsupported_preview_explains_without_writing(db, learner):
    task, _, _ = await setup_task(db)
    task.kind = "code"
    await db.commit()
    result = await task_reviews.preview(db, learner.id, task.id)
    assert not result.reviewable and result.unavailable_reason
    assert await db.scalar(select(func.count()).select_from(AssessmentTaskReview)) == 0


async def test_review_api_preview_confirm_replay_and_stale_content(client, db):
    task, _, _ = await setup_task(db)
    path = f"/api/questions/{task.id}/task-review"
    response = await client.get(path)
    assert response.status_code == 200
    preview = response.json()
    assert preview["content"]["item"] == {"prompt": "Why?"}
    assert not preview["approval_matches_content"]
    body = {
        "request_id": str(uuid4()),
        "expected_revision": 0,
        "content_version": preview["content_version"],
        "decision": "approve",
        "facet": "explanation",
        "confirmed": False,
    }
    assert (await client.post(path, json=body)).status_code == 409
    body["confirmed"] = True
    approved = await client.post(path, json=body)
    assert approved.status_code == 200
    assert (await client.post(path, json=body)).json() == approved.json()
    assert (await client.get(path)).json()["approval_matches_content"]
    task.item_json = {"prompt": "Changed after preview"}
    await db.commit()
    changed = await client.get(path)
    assert not changed.json()["approval_matches_content"]
    body.update(request_id=str(uuid4()), expected_revision=1)
    assert (await client.post(path, json=body)).status_code == 409
    assert (await client.get("/api/questions/unknown/task-review")).status_code == 404


async def test_review_api_rejects_another_learners_private_task(client, db):
    task, _, _ = await setup_task(db)
    path = f"/api/questions/{task.id}/task-review"
    preview = (await client.get(path)).json()
    other = LearnerProfile(display_name="Private author")
    db.add(other)
    await db.flush()
    # Deliberate fixture corruption to retain defensive access checks.
    await db.execute(text("DROP TRIGGER assessment_owner_immutable"))
    task.owner_learner_id = other.id
    await db.commit()
    assert (await client.get(path)).status_code == 404
    response = await client.post(
        path,
        json={
            "request_id": str(uuid4()),
            "expected_revision": 0,
            "content_version": preview["content_version"],
            "decision": "approve",
            "facet": "explanation",
            "confirmed": True,
        },
    )
    assert response.status_code == 404
    assert await db.scalar(select(func.count()).select_from(AssessmentTaskReview)) == 0


async def test_capture_is_explicit_none_until_exact_approval(db, learner):
    task, _, _ = await setup_task(db)
    content = await task_reviews.snapshot(db, learner.id, task.id)
    absent = await task_reviews.capture(db, learner.id, task.id, content)
    assert absent.model_dump() == {"schema_version": 1, "review": None}
    body = await command(db, learner.id, task.id)
    receipt = await task_reviews.decide(db, learner.id, task.id, body)
    await db.commit()
    captured = await task_reviews.capture(db, learner.id, task.id, content)
    assert captured.review.receipt_id == receipt.id
    assert absent.review is None  # later approval cannot rewrite the captured value
    revoke = await command(db, learner.id, task.id, decision="revoke", expected_revision=1)
    await task_reviews.decide(db, learner.id, task.id, revoke)
    await db.commit()
    assert (await task_reviews.capture(db, learner.id, task.id, content)).review is None
    assert captured.review.receipt_id == receipt.id


@pytest.mark.parametrize("target", ["task", "rubric", "objective"])
async def test_capture_rejects_edits_since_pre_inference_read(db, learner, target):
    task, rubric, skill = await setup_task(db)
    content = await task_reviews.snapshot(db, learner.id, task.id)
    if target == "task":
        task.item_json = {"prompt": "New task"}
    elif target == "rubric":
        rubric.criteria_json = [{"criterion": "New criterion"}]
    else:
        skill.description = "New objective"
    await db.commit()
    with pytest.raises(AppError, match="changed"):
        await task_reviews.capture(db, learner.id, task.id, content)


async def test_restore_uses_historical_receipt_never_later_approval(db, learner):
    task, _, _ = await setup_task(db)
    content = await task_reviews.snapshot(db, learner.id, task.id)
    absent = (await task_reviews.capture(db, learner.id, task.id, content)).model_dump()
    approved = await task_reviews.decide(
        db, learner.id, task.id, await command(db, learner.id, task.id)
    )
    await db.commit()
    saved = (await task_reviews.capture(db, learner.id, task.id, content)).model_dump()
    await task_reviews.decide(
        db,
        learner.id,
        task.id,
        await command(db, learner.id, task.id, decision="revoke", expected_revision=1),
    )
    await db.commit()
    assert (
        await task_reviews.restore_binding(db, learner.id, task.id, saved)
    ).review.receipt_id == approved.id
    assert (await task_reviews.restore_binding(db, learner.id, task.id, absent)).review is None
    assert await task_reviews.restore_binding(db, learner.id, task.id, None) is None
    assert (
        await task_reviews.restore_binding(db, learner.id, task.id, {"schema_version": 99}) is None
    )
    assert await task_reviews.restore_binding(db, "foreign-owner", task.id, saved) is None
    assert await task_reviews.restore_binding(db, learner.id, "wrong-task", saved) is None


async def test_restore_refuses_missing_binding_version(db, learner):
    task, _, _ = await setup_task(db)
    assert await task_reviews.restore_binding(db, learner.id, task.id, {"review": None}) is None


async def test_concurrent_approval_waits_for_preparation_capture(db, learner):
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.db import assessment_executions
    from tests.test_assessment_executions import new_claim

    task, _, _ = await setup_task(db)
    owner, task_id = learner.id, task.id
    claim_id = await new_claim(db, learner)
    content = await task_reviews.snapshot(db, owner, task_id)
    approval = await command(db, owner, task_id)
    await db.commit()
    sessions = async_sessionmaker(db.bind, expire_on_commit=False)
    captured, release, approval_started = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def prepare():
        async with sessions() as conn:

            async def capture():
                value = await task_reviews.capture(conn, owner, task_id, content)
                captured.set()
                await asyncio.wait_for(release.wait(), 5)
                return value.model_dump()

            await assessment_executions.prepare(
                conn,
                owner,
                claim_id,
                request_json={"answer": "original"},
                content_fingerprint="original",
                capture_review=capture,
            )

    async def approve():
        async with sessions() as conn:
            approval_started.set()
            await task_reviews.decide(conn, owner, task_id, approval)
            await conn.commit()

    preparation = asyncio.create_task(prepare())
    await asyncio.wait_for(captured.wait(), 5)
    decision = asyncio.create_task(approve())
    await asyncio.wait_for(approval_started.wait(), 5)
    release.set()
    await asyncio.gather(preparation, decision)
    saved = await assessment_executions.get_owned(db, owner, claim_id)
    assert saved.task_review_json == {"schema_version": 1, "review": None}
    assert (await task_reviews.latest(db, owner, task_id)).decision == "approve"
