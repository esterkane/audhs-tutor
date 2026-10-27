"""Single-learner convenience (Phase 1): the owner profile is created on first use."""

from sqlalchemy import JSON, exists, insert, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id, utcnow_iso
from app.db.models import LearnerProfile


async def get_or_create_owner(db: AsyncSession, display_name: str = "Saru") -> LearnerProfile:
    row = (
        (
            await db.execute(
                select(LearnerProfile).order_by(LearnerProfile.created_at, LearnerProfile.id)
            )
        )
        .scalars()
        .first()
    )
    if row is None:
        # One conditional write, rather than a separate read/insert race on first page load.
        await db.execute(
            insert(LearnerProfile).from_select(
                ["id", "display_name", "settings_json", "created_at"],
                select(
                    literal(new_id()),
                    literal(display_name),
                    literal({}, type_=JSON),
                    literal(utcnow_iso()),
                ).where(~exists(select(LearnerProfile.id))),
            )
        )
        await db.commit()
        row = await db.scalar(
            select(LearnerProfile).order_by(LearnerProfile.created_at, LearnerProfile.id)
        )
        assert row is not None
    return row
