"""Single-learner convenience (Phase 1): the owner profile is created on first use."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearnerProfile


async def get_or_create_owner(db: AsyncSession, display_name: str = "Saru") -> LearnerProfile:
    row = (
        (await db.execute(select(LearnerProfile).order_by(LearnerProfile.created_at)))
        .scalars()
        .first()
    )
    if row is None:
        row = LearnerProfile(display_name=display_name)
        db.add(row)
        await db.commit()
    return row
