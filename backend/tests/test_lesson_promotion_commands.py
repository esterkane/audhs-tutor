import asyncio
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update

from app.core.errors import AppError
from app.db.models import (
    Assessment,
    AssessmentAttempt,
    CurriculumDraft,
    LearningEvent,
    LearningObject,
    LessonPromotion,
    LessonPromotionSnapshot,
    ModelCall,
    TutorAnswer,
)
from app.kernel import curriculum
from app.kernel.answer_lesson_binding import resolve_lesson_binding
from app.kernel.lesson_promotion import LessonPromotionRepository
from tests.test_answer_visual_binding import saved


async def body(db, learner):
    answer = await saved(db, learner)
    resolved = await resolve_lesson_binding(db, learner.id, answer.id)
    await db.commit()
    return {
        "binding": resolved.binding.model_dump(mode="json"),
        "domain": "ai_ml",
        "title": "Fit and transform",
        "objective": "Distinguish fitting from applying a parameter.",
        "explanation": "Fit a mean on training data, then apply the saved mean.",
        "worked_example": "Training values 2 and 4 have mean 3.",
        "question": "Which records should determine the imputation median and why?",
        "criteria": ["Use observed training values only.", "Apply the same median to both sets."],
    }


def raw(value):
    return json.dumps(value).encode()


async def test_atomic_create_and_parallel_retry_preserve_content(db, learner, session_factory):
    command = await body(db, learner)
    repo = LessonPromotionRepository(session_factory)
    a, b = await asyncio.gather(
        *[repo.create(learner.id, "same-key", raw(command)) for _ in range(2)]
    )
    assert a == b
    async with session_factory() as check:
        draft = await check.get(CurriculumDraft, a.draft_id)
        assert draft.status == "draft" and draft.origin == "answer_derived"
        assert draft.payload_json["assessments"][0]["rubric"] == [
            {"criterion": c} for c in command["criteria"]
        ]
        assert draft.payload_json["learning_objects"][0]["sources"] == []
        assert await check.scalar(select(func.count()).select_from(LessonPromotion)) == 1
        assert await check.scalar(select(func.count()).select_from(LessonPromotionSnapshot)) == 1
        for model in (Assessment, AssessmentAttempt, LearningObject, LearningEvent, ModelCall):
            assert await check.scalar(select(func.count()).select_from(model)) == 0
        with pytest.raises(AppError, match="remains private"):
            await curriculum.publish_draft(check, learner.id, draft.id)


async def test_retry_returns_creation_receipt_after_edit_and_source_change(
    db, learner, session_factory
):
    command = await body(db, learner)
    repo = LessonPromotionRepository(session_factory)
    original = await repo.create(learner.id, "key", raw(command))
    async with session_factory() as other:
        await other.execute(
            update(CurriculumDraft)
            .where(CurriculumDraft.id == original.draft_id)
            .values(version=2, title="Later edits")
        )
        await other.execute(
            update(TutorAnswer).where(TutorAnswer.id == "root").values(text="Changed")
        )
        await other.commit()
    assert await repo.create(learner.id, "key", raw(command)) == original
    with pytest.raises(AppError, match="different content"):
        await repo.create(learner.id, "key", raw({**command, "title": "New request"}))
    with pytest.raises(AppError, match="changed"):
        await repo.create(learner.id, "new-key", raw(command))
    async with session_factory() as check:
        draft = await check.get(CurriculumDraft, original.draft_id)
        assert draft.title == "Later edits" and draft.version == 2
        assert await check.scalar(select(func.count()).select_from(CurriculumDraft)) == 1


async def test_foreign_missing_and_invalid_commands_leave_no_partial_records(
    db, learner, session_factory
):
    command = await body(db, learner)
    repo = LessonPromotionRepository(session_factory)
    with pytest.raises(KeyError):
        await repo.create("foreign", "key", raw(command))
    with pytest.raises(ValueError, match="validation"):
        await repo.create(learner.id, "key", raw({**command, "prerequisites": ["unknown-skill"]}))
    with pytest.raises(ValidationError):
        await repo.create(learner.id, "key", raw({**command, "criteria": ["same", "SAME"]}))
    with pytest.raises(ValidationError):
        await repo.create(learner.id, "key", raw({**command, "origin": "owner_authored"}))
    with pytest.raises(ValueError, match="size"):
        await repo.create(learner.id, "key", b" " * 65537)
    async with session_factory() as check:
        for model in (CurriculumDraft, LessonPromotion, LessonPromotionSnapshot):
            assert await check.scalar(select(func.count()).select_from(model)) == 0


async def test_snapshot_insert_failure_rolls_back_draft_and_receipt(db, learner, session_factory):
    from sqlalchemy import event

    command = await body(db, learner)
    repo = LessonPromotionRepository(session_factory)

    def fail_snapshot(*args):
        raise RuntimeError("Synthetic snapshot storage failure")

    event.listen(LessonPromotionSnapshot, "before_insert", fail_snapshot)
    try:
        with pytest.raises(RuntimeError, match="snapshot storage failure"):
            await repo.create(learner.id, "atomic-key", raw(command))
    finally:
        event.remove(LessonPromotionSnapshot, "before_insert", fail_snapshot)
    async with session_factory() as check:
        for model in (CurriculumDraft, LessonPromotion, LessonPromotionSnapshot):
            assert await check.scalar(select(func.count()).select_from(model)) == 0
    receipt = await repo.create(learner.id, "atomic-key", raw(command))
    assert receipt.created_version == 1
