"""Explicit, idempotent active-map reset; historical rows and answers are preserved."""

from sqlalchemy import func, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow_iso
from app.db.models import (
    KnowledgeArea,
    LearnerPreference,
    ReviewItem,
    Session,
    SkillNode,
)
from app.kernel.learning_scope import FOCUS_TOPICS, REFERENCE_BEFORE, reference_before

TOPIC_SLUGS = ["elasticsearch", "vector-search", "supabase", "postgresql", "qdrant", "kubernetes"]


async def plan(db: AsyncSession, learner_id: str) -> dict[str, object]:
    return {
        "reference_before": await reference_before(db, learner_id),
        "historical_skills_retained": await db.scalar(select(func.count()).select_from(SkillNode)),
        "historical_sessions_retained": await db.scalar(
            select(func.count()).select_from(Session).where(Session.learner_id == learner_id)
        ),
        "active_sessions_to_end": await db.scalar(
            select(func.count())
            .select_from(Session)
            .where(Session.learner_id == learner_id, Session.ended_at.is_(None))
        ),
        "review_items_to_retire": await db.scalar(
            select(func.count())
            .select_from(ReviewItem)
            .where(ReviewItem.learner_id == learner_id, ReviewItem.active.is_(True))
        ),
        "topics": FOCUS_TOPICS,
        "purges_course_files": False,
    }


async def apply(db: AsyncSession, learner_id: str) -> str:
    existing = await reference_before(db, learner_id)
    if existing is not None:
        return existing
    cutoff = utcnow_iso()
    claimed = await db.scalar(
        insert(LearnerPreference)
        .values(learner_id=learner_id, key=REFERENCE_BEFORE, value_json=cutoff, origin="explicit")
        .on_conflict_do_nothing(index_elements=["learner_id", "key"])
        .returning(LearnerPreference.id)
    )
    if claimed is None:
        await db.rollback()
        existing = await reference_before(db, learner_id)
        assert existing is not None
        return existing
    for slug, title in zip(TOPIC_SLUGS, FOCUS_TOPICS, strict=True):
        await db.execute(
            insert(KnowledgeArea)
            .values(
                slug="focus-" + slug,
                title=title,
                terms_json=[title],
                description=(
                    "Create and explicitly accept your own knowledge material "
                    "from notes, research and optional uploads."
                ),
            )
            .on_conflict_do_nothing(index_elements=["slug"])
        )
    await db.execute(
        update(ReviewItem)
        .where(ReviewItem.learner_id == learner_id, ReviewItem.created_at <= cutoff)
        .values(active=False)
    )
    await db.execute(
        update(Session)
        .where(
            Session.learner_id == learner_id,
            Session.started_at <= cutoff,
            Session.ended_at.is_(None),
        )
        .values(ended_at=cutoff)
    )
    await db.commit()
    return cutoff
