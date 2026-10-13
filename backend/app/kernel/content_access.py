"""Explicit shared-or-owned curriculum reads. No production private writer enabled yet.

These helpers are a foundation, not a global ORM policy. Consumers must use them
before private content can be activated. Missing scope intentionally sees shared only.
"""

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import AppError
from app.db.models import LearningObject, Representation, SkillNode


def skill_visible(learner_id: str | None) -> ColumnElement[bool]:
    shared = SkillNode.owner_learner_id.is_(None)
    return shared if learner_id is None else or_(shared, SkillNode.owner_learner_id == learner_id)


def object_visible(learner_id: str | None) -> ColumnElement[bool]:
    return exists().where(SkillNode.id == LearningObject.skill_id, skill_visible(learner_id))


def representation_visible(learner_id: str | None) -> ColumnElement[bool]:
    return exists().where(LearningObject.id == Representation.object_id, object_visible(learner_id))


async def require_skill(db: AsyncSession, learner_id: str | None, skill_id: str) -> SkillNode:
    row = await db.scalar(
        select(SkillNode)
        .where(SkillNode.id == skill_id, skill_visible(learner_id))
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise AppError("not_found", "This learning material is unavailable.", 404)
    return row


async def require_object(
    db: AsyncSession, learner_id: str | None, object_id: str
) -> LearningObject:
    row = await db.scalar(
        select(LearningObject)
        .where(LearningObject.id == object_id, object_visible(learner_id))
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise AppError("not_found", "This learning material is unavailable.", 404)
    return row


async def require_representation(
    db: AsyncSession, learner_id: str | None, representation_id: str
) -> Representation:
    row = await db.scalar(
        select(Representation)
        .where(Representation.id == representation_id, representation_visible(learner_id))
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise AppError("not_found", "This learning material is unavailable.", 404)
    return row


async def shared_nodes_by_slug(db: AsyncSession, slugs: list[str]) -> dict[str, SkillNode]:
    """Preflight shared writers before any mutation; private slug collisions cannot be adopted."""
    rows = list(
        await db.scalars(
            select(SkillNode)
            .where(SkillNode.slug.in_(slugs))
            .execution_options(populate_existing=True)
        )
    )
    if any(row.owner_learner_id is not None for row in rows):
        raise AppError("content_conflict", "A requested content identifier is unavailable.", 409)
    return {row.slug: row for row in rows}
