"""Derived embedding cache. Callers compute vectors outside database transactions."""

import math

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.answer_eligibility import excluded_answer_ids
from app.db.base import new_id, utcnow_iso
from app.db.models import TutorAnswer, TutorAnswerVector


def valid(vector: list[float]) -> bool:
    try:
        return (
            0 < len(vector) <= 8192
            and all(
                isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x)
                for x in vector
            )
            and any(x != 0 for x in vector)
        )
    except (OverflowError, TypeError):
        return False


async def put(
    db: AsyncSession,
    learner_id: str,
    answer_id: str,
    fingerprint: str,
    model_key: str,
    vector: list[float],
) -> bool:
    if not model_key or len(model_key) > 500 or not valid(vector):
        raise ValueError("Invalid embedding cache entry")
    # An embedding computed for deleted/edited/foreign work must not be attached to current work.
    answer = await db.scalar(
        select(TutorAnswer.id).where(
            TutorAnswer.id == answer_id,
            TutorAnswer.learner_id == learner_id,
            TutorAnswer.fingerprint == fingerprint,
        )
    )
    if answer is None:
        return False
    values = dict(
        answer_fingerprint=fingerprint,
        model_key=model_key,
        vector_json=vector,
        updated_at=utcnow_iso(),
    )
    stmt = insert(TutorAnswerVector).values(
        id=new_id(), learner_id=learner_id, answer_id=answer_id, **values
    )
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[TutorAnswerVector.learner_id, TutorAnswerVector.answer_id],
            set_=values,
        )
    )
    await db.commit()
    return True


async def load(
    db: AsyncSession,
    learner_id: str,
    answer_ids: list[str],
    model_key: str,
    dims: int,
) -> dict[str, list[float]]:
    """Only current, visible, owner-scoped candidates; caller scopes targets before ranking."""
    if len(answer_ids) > 256 or not 0 < dims <= 8192:
        raise ValueError("Embedding lookup bounds exceeded")
    excluded = excluded_answer_ids(learner_id)
    stmt = (
        select(TutorAnswerVector)
        .join(TutorAnswer, TutorAnswer.id == TutorAnswerVector.answer_id)
        .where(
            TutorAnswerVector.learner_id == learner_id,
            TutorAnswer.learner_id == learner_id,
            TutorAnswerVector.answer_id.in_(answer_ids),
            TutorAnswer.id.not_in(excluded),
            TutorAnswerVector.answer_fingerprint == TutorAnswer.fingerprint,
            TutorAnswerVector.model_key == model_key,
        )
    )
    rows = await db.scalars(stmt)
    return {
        row.answer_id: row.vector_json
        for row in rows
        if isinstance(row.vector_json, list)
        and len(row.vector_json) == dims
        and valid(row.vector_json)
    }
