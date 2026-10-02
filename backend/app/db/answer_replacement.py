"""Explicit reviewed preference; never rewrites answers, feedback or learning evidence."""

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.answer_feedback import owned
from app.db.base import utcnow_iso
from app.db.models import TutorAnswer, TutorAnswerReplacement
from app.schemas.answers import AnswerReplacementState


async def read(db: AsyncSession, learner_id: str, answer_id: str) -> AnswerReplacementState:
    await owned(db, learner_id, answer_id)
    row = await db.scalar(
        select(TutorAnswerReplacement)
        .where(
            TutorAnswerReplacement.learner_id == learner_id,
            TutorAnswerReplacement.answer_id == answer_id,
        )
        .execution_options(populate_existing=True)
    )
    return (
        AnswerReplacementState(replacement_id=row.replacement_id, revision=row.revision)
        if row
        else AnswerReplacementState()
    )


async def save(
    db: AsyncSession, learner_id: str, answer_id: str, body: AnswerReplacementState
) -> AnswerReplacementState:
    current = await read(db, learner_id, answer_id)
    if current.replacement_id == body.replacement_id:
        return current
    if current.revision != body.revision:
        raise AppError(
            "replacement_conflict",
            "Your preferred reply changed elsewhere. Review the latest choice.",
            409,
        )
    if body.replacement_id is not None:
        target = await db.scalar(
            select(TutorAnswer).where(
                TutorAnswer.id == body.replacement_id, TutorAnswer.learner_id == learner_id
            )
        )
        if target is None:
            raise KeyError("saved answer not found")
        if (
            target.id == answer_id
            or target.metadata_json.get("parent_answer_id") != answer_id
            or target.metadata_json.get("followup_purpose") != "correction"
        ):
            raise AppError(
                "invalid_replacement",
                "Choose a proposed correction made directly from this answer.",
                422,
            )
        from app.db.answer_eligibility import excluded_answer_ids

        if await db.scalar(
            select(TutorAnswer.id).where(
                TutorAnswer.id == target.id, TutorAnswer.id.in_(excluded_answer_ids(learner_id))
            )
        ):
            raise AppError(
                "invalid_replacement",
                "This correction is hidden, reported incorrect/outdated, or already replaced. "
                "Review its feedback first.",
                409,
            )
    values = {
        "replacement_id": body.replacement_id,
        "revision": body.revision + 1,
        "updated_at": utcnow_iso(),
    }
    try:
        if body.revision == 0:
            stmt = (
                insert(TutorAnswerReplacement)
                .values(learner_id=learner_id, answer_id=answer_id, **values)
                .on_conflict_do_nothing(index_elements=["learner_id", "answer_id"])
                .returning(TutorAnswerReplacement.id)
            )
            changed = (await db.execute(stmt)).scalar_one_or_none()
        else:
            update_stmt = (
                update(TutorAnswerReplacement)
                .where(
                    TutorAnswerReplacement.learner_id == learner_id,
                    TutorAnswerReplacement.answer_id == answer_id,
                    TutorAnswerReplacement.revision == body.revision,
                )
                .values(**values)
                .returning(TutorAnswerReplacement.id)
            )
            changed = (await db.execute(update_stmt)).scalar_one_or_none()
        if changed is None:
            await db.rollback()
            latest = await read(db, learner_id, answer_id)
            if latest.replacement_id == body.replacement_id:
                return latest
            raise AppError(
                "replacement_conflict",
                "Your preferred reply changed elsewhere. Review the latest choice.",
                409,
            )
        await db.commit()
        return AnswerReplacementState(
            replacement_id=body.replacement_id, revision=body.revision + 1
        )
    except BaseException:
        await db.rollback()
        raise
