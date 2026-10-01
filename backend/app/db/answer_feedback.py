"""Revision-checked explicit reports. No answer rewrite, learning event or mastery change."""

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow_iso
from app.db.models import TutorAnswer, TutorAnswerFeedback
from app.schemas.answers import AnswerFeedbackState


async def owned(db: AsyncSession, learner_id: str, answer_id: str) -> None:
    if (
        await db.scalar(
            select(TutorAnswer.id).where(
                TutorAnswer.id == answer_id, TutorAnswer.learner_id == learner_id
            )
        )
        is None
    ):
        raise KeyError("saved answer not found")


async def read(db: AsyncSession, learner_id: str, answer_id: str) -> AnswerFeedbackState:
    await owned(db, learner_id, answer_id)
    row = await db.scalar(
        select(TutorAnswerFeedback)
        .where(
            TutorAnswerFeedback.learner_id == learner_id, TutorAnswerFeedback.answer_id == answer_id
        )
        .execution_options(populate_existing=True)
    )
    return (
        AnswerFeedbackState.model_validate(
            {
                "verdict": row.verdict,
                "note": row.note,
                "hidden": row.hidden,
                "revision": row.revision,
            }
        )
        if row
        else AnswerFeedbackState()
    )


async def save(
    db: AsyncSession, learner_id: str, answer_id: str, body: AnswerFeedbackState
) -> AnswerFeedbackState:
    current = await read(db, learner_id, answer_id)
    wanted = body.model_dump(exclude={"revision"})
    if current.model_dump(exclude={"revision"}) == wanted:
        return current  # same-state retry is harmless even with an older revision
    if current.revision != body.revision:
        raise AppError(
            "feedback_conflict", "Feedback changed elsewhere. Reload it before saving.", 409
        )
    values = {**wanted, "revision": body.revision + 1, "updated_at": utcnow_iso()}
    try:
        if body.revision == 0:
            stmt = (
                insert(TutorAnswerFeedback)
                .values(learner_id=learner_id, answer_id=answer_id, **values)
                .on_conflict_do_nothing(index_elements=["learner_id", "answer_id"])
                .returning(TutorAnswerFeedback.id)
            )
            changed = (await db.execute(stmt)).scalar_one_or_none()
        else:
            update_stmt = (
                update(TutorAnswerFeedback)
                .where(
                    TutorAnswerFeedback.learner_id == learner_id,
                    TutorAnswerFeedback.answer_id == answer_id,
                    TutorAnswerFeedback.revision == body.revision,
                )
                .values(**values)
                .returning(TutorAnswerFeedback.id)
            )
            changed = (await db.execute(update_stmt)).scalar_one_or_none()
        if changed is None:
            await db.rollback()
            latest = await read(db, learner_id, answer_id)
            if latest.model_dump(exclude={"revision"}) == wanted:
                return latest
            raise AppError(
                "feedback_conflict", "Feedback changed elsewhere. Reload it before saving.", 409
            )
        await db.commit()
        return AnswerFeedbackState(**values)
    except BaseException:
        await db.rollback()
        raise
