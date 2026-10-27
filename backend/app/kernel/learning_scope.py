"""Owner-selected clean-slate curriculum boundary; historical records stay intact."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import AppError
from app.db.models import LearnerPreference

REFERENCE_BEFORE = "learning.reference_before"
FOCUS_TOPICS = ["Elasticsearch", "Vector search", "Supabase", "PostgreSQL", "Qdrant", "Kubernetes"]


def created_visible(learner_id: str | None, created_at: Any) -> ColumnElement[bool]:
    if learner_id is None:
        return true()
    cutoff = (
        select(func.json_extract(LearnerPreference.value_json, "$"))
        .where(
            LearnerPreference.learner_id == learner_id, LearnerPreference.key == REFERENCE_BEFORE
        )
        .scalar_subquery()
    )
    return or_(cutoff.is_(None), created_at > cutoff)


async def reference_before(db: AsyncSession, learner_id: str) -> str | None:
    value = await db.scalar(
        select(LearnerPreference.value_json).where(
            LearnerPreference.learner_id == learner_id, LearnerPreference.key == REFERENCE_BEFORE
        )
    )
    if value is None:
        return None
    try:
        if not isinstance(value, str):
            raise ValueError()
        datetime.fromisoformat(value)
    except ValueError as error:
        raise AppError(
            "learning_scope_invalid", "The learning catalogue boundary needs repair.", 503
        ) from error
    return value


async def require_current_material(db: AsyncSession, learner_id: str, created_at: str) -> None:
    cutoff = await reference_before(db, learner_id)
    if cutoff is not None and created_at <= cutoff:
        raise AppError(
            "accuracy_review_only",
            (
                "This historical material is retained for accuracy review only. Create new material "
                "from your notes or uploads."
            ),
            409,
        )
