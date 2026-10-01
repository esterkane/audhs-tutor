"""Read helpers over learning_event. Services call these instead of ad-hoc SQL."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningEvent


async def events_for_session(db: AsyncSession, session_id: str) -> Sequence[LearningEvent]:
    stmt = (
        select(LearningEvent)
        .where(LearningEvent.session_id == session_id)
        .order_by(LearningEvent.ts)
    )
    return (await db.execute(stmt)).scalars().all()


async def count_by_verb(db: AsyncSession, learner_id: str) -> dict[str, int]:
    stmt = (
        select(LearningEvent.verb, func.count())
        .where(LearningEvent.learner_id == learner_id)
        .group_by(LearningEvent.verb)
    )
    return {verb: n for verb, n in (await db.execute(stmt)).all()}


async def last_event(
    db: AsyncSession, learner_id: str, verb: str | None = None
) -> LearningEvent | None:
    stmt = select(LearningEvent).where(LearningEvent.learner_id == learner_id)
    if verb:
        stmt = stmt.where(LearningEvent.verb == verb)
    stmt = stmt.order_by(LearningEvent.ts.desc()).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()
