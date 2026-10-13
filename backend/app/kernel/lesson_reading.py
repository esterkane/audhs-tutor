"""Read saved private teaching content without generation or learning-state writes."""

import hashlib
import json

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import (
    LearningObject,
    LessonActivation,
    LessonActivationObject,
    LessonPromotion,
    SkillNode,
)
from app.kernel import content_access, skill_graph


class LessonReading(BaseModel):
    object_id: str
    object_version: int
    content_sha256: str
    concept: str
    goal: str
    passages: list[str]
    source_ids: list[str]
    activation_id: str
    draft_id: str
    answer_id: str


async def read(db: AsyncSession, learner_id: str, skill_id: str) -> LessonReading | None:
    try:
        await skill_graph.get_node(db, skill_id, learner_id=learner_id)
    except KeyError as exc:
        raise AppError("not_found", "Lesson not found.", http_status=404) from exc
    latest = (
        select(LearningObject.id)
        .where(LearningObject.skill_id == skill_id, content_access.object_visible(learner_id))
        .order_by(LearningObject.version.desc(), LearningObject.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    row = (
        await db.execute(
            select(
                LearningObject,
                LessonActivation.id,
                LessonPromotion.draft_id,
                LessonPromotion.answer_id,
            )
            .join(SkillNode, SkillNode.id == LearningObject.skill_id)
            .join(LessonActivationObject, LessonActivationObject.entity_id == LearningObject.id)
            .join(LessonActivation, LessonActivation.id == LessonActivationObject.activation_id)
            .join(LessonPromotion, LessonPromotion.id == LessonActivation.promotion_id)
            .where(
                LearningObject.id == latest,
                SkillNode.owner_learner_id == learner_id,
                LessonActivationObject.learner_id == learner_id,
                LessonActivation.learner_id == learner_id,
                LessonPromotion.learner_id == learner_id,
            )
        )
    ).one_or_none()
    if row is None:
        return None
    obj, activation_id, draft_id, answer_id = row
    passages = [value for value in obj.examples_json if isinstance(value, str) and value.strip()]
    if not passages:
        return None
    sources = [value for value in obj.sources_json if isinstance(value, str)]
    identity = json.dumps(
        [obj.id, obj.version, obj.concept, obj.goal, passages, sources], ensure_ascii=False
    )
    return LessonReading(
        object_id=obj.id,
        object_version=obj.version,
        content_sha256=hashlib.sha256(identity.encode()).hexdigest(),
        concept=obj.concept,
        goal=obj.goal,
        passages=passages,
        source_ids=sources,
        activation_id=activation_id,
        draft_id=draft_id,
        answer_id=answer_id,
    )
