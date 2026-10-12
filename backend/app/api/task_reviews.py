"""Explicit authoring review, separate from practice and performance evidence."""

from fastapi import APIRouter

from app.api.deps import DB, Learner
from app.kernel import task_reviews
from app.schemas.task_reviews import TaskReviewCommand, TaskReviewPreview, TaskReviewReceipt

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get(
    "/{assessment_id}/task-review",
    response_model=TaskReviewPreview,
    summary="Inspect the exact task, objective and rubric before authoring review",
)
async def preview(assessment_id: str, db: DB, learner: Learner) -> TaskReviewPreview:
    return await task_reviews.preview(db, learner.id, assessment_id)


@router.post(
    "/{assessment_id}/task-review",
    response_model=TaskReviewReceipt,
    summary="Explicitly approve or revoke task and rubric review for yourself",
)
async def decide(
    assessment_id: str, body: TaskReviewCommand, db: DB, learner: Learner
) -> TaskReviewReceipt:
    learner_id = learner.id
    await db.commit()
    try:
        result = await task_reviews.decide(db, learner_id, assessment_id, body)
        await db.commit()
        return result
    except BaseException:
        await db.rollback()
        raise
