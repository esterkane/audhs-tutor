"""Atomic local private activation. No inference, public publication or learning evidence."""

import hashlib
import json
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.base import new_id, utcnow_iso
from app.db.models import (
    Assessment,
    AssessmentRubric,
    CurriculumDraft,
    LearningObject,
    LessonActivation,
    LessonActivationAssessment,
    LessonActivationEdge,
    LessonActivationObject,
    LessonActivationSkill,
    LessonPromotion,
    SkillEdge,
    SkillNode,
)
from app.kernel import curriculum
from app.kernel.answer_lesson_binding import validate_lesson_binding
from app.kernel.content_access import skill_visible
from app.schemas.answer_lesson_binding import AnswerLessonBinding
from app.schemas.common import Domain
from app.schemas.curriculum import DraftPayload
from app.schemas.lesson_activation import ActivateLesson, LessonActivationReceipt

MAX_COMMAND_BYTES = 4096
MAX_PAYLOAD_BYTES = 1048576


def canonical_payload(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def payload_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload(payload).encode()).hexdigest()


def conflict(message: str) -> AppError:
    return AppError("activation_conflict", message, 409)


async def _receipt(db: AsyncSession, row: LessonActivation) -> LessonActivationReceipt:
    promotion = await db.get(LessonPromotion, row.promotion_id)
    if promotion is None or promotion.learner_id != row.learner_id:
        raise conflict("Activation history is unavailable.")

    async def ids(model: Any) -> tuple[str, ...]:
        return tuple(
            (
                await db.scalars(
                    select(model.entity_id)
                    .where(model.learner_id == row.learner_id, model.activation_id == row.id)
                    .order_by(model.entity_id)
                )
            ).all()
        )

    return LessonActivationReceipt(
        activation_id=row.id,
        promotion_id=row.promotion_id,
        draft_id=promotion.draft_id,
        activated_version=row.draft_version,
        payload_sha256=row.payload_sha256,
        skill_ids=await ids(LessonActivationSkill),
        object_ids=await ids(LessonActivationObject),
        assessment_ids=await ids(LessonActivationAssessment),
        edge_ids=await ids(LessonActivationEdge),
    )


class LessonActivationRepository:
    def __init__(self, factory: async_sessionmaker[AsyncSession]):
        self.factory = factory

    async def get(self, learner_id: str, activation_id: str) -> LessonActivationReceipt:
        async with self.factory() as db:
            # One read snapshot prevents a concurrent wipe from splitting a receipt.
            await db.execute(text("BEGIN"))
            row = await db.scalar(
                select(LessonActivation).where(
                    LessonActivation.id == activation_id, LessonActivation.learner_id == learner_id
                )
            )
            if row is None:
                raise AppError("not_found", "Activation not found.", 404)
            return await _receipt(db, row)

    async def activate(
        self, learner_id: str, request_key: str, raw: bytes
    ) -> LessonActivationReceipt:
        if not request_key.strip() or len(request_key) > 128 or len(raw) > MAX_COMMAND_BYTES:
            raise ValueError("Invalid activation request identity or size")
        command = ActivateLesson.model_validate_json(raw)
        fingerprint = payload_digest(command.model_dump(mode="json"))
        async with self.factory() as db:
            try:
                await db.execute(text("BEGIN IMMEDIATE"))
                prior = await db.scalar(
                    select(LessonActivation).where(
                        LessonActivation.learner_id == learner_id,
                        LessonActivation.request_key == request_key,
                    )
                )
                if prior is not None:
                    if prior.fingerprint != fingerprint:
                        raise conflict("Request identity already used for different content.")
                    receipt = await _receipt(db, prior)
                    await db.rollback()
                    return receipt
                promotion = await db.scalar(
                    select(LessonPromotion).where(
                        LessonPromotion.id == command.promotion_id,
                        LessonPromotion.learner_id == learner_id,
                    )
                )
                if promotion is None:
                    raise AppError("not_found", "Lesson draft not found.", 404)
                if await db.scalar(
                    select(LessonActivation.id).where(LessonActivation.promotion_id == promotion.id)
                ):
                    raise conflict("Lesson already activated under another request identity.")
                draft = await db.scalar(
                    select(CurriculumDraft).where(
                        CurriculumDraft.id == promotion.draft_id,
                        CurriculumDraft.learner_id == learner_id,
                    )
                )
                if draft is None or draft.status != "draft":
                    raise conflict("Lesson is no longer an editable draft.")
                frozen = canonical_payload(draft.payload_json)
                if len(frozen.encode()) > MAX_PAYLOAD_BYTES:
                    raise ValueError("Lesson payload exceeds activation size limit")
                if (
                    draft.version != command.expected_version
                    or payload_digest(draft.payload_json) != command.payload_sha256
                ):
                    raise conflict("Lesson draft changed. Review the current version.")
                try:
                    binding = AnswerLessonBinding.model_validate_json(promotion.binding_json)
                    await validate_lesson_binding(db, learner_id, binding)
                except (ValueError, KeyError):
                    raise conflict(
                        "Answer or source history changed. The draft has been retained."
                    ) from None
                payload = DraftPayload.model_validate(draft.payload_json)
                Domain(payload.domain)
                # Each skill has one initial object version; ambiguous duplicates must not be collapsed.
                object_skills = [o.skill for o in payload.learning_objects]
                if len(set(object_skills)) != len(object_skills):
                    raise ValueError("Duplicate learning-object mappings")
                slugs = [s.slug for s in payload.skills]
                if len(set(slugs)) != len(slugs):
                    raise ValueError("Duplicate skill mappings")
                ids = {slug: new_id() for slug in slugs}
                # Draft identifiers are local aliases, never existing-node upserts. Remap for cycle checks too.
                mapped = payload.model_dump(mode="json")
                aliases = {
                    slug: f"private-lesson-{identity.lower()}" for slug, identity in ids.items()
                }
                for skill in mapped["skills"]:
                    skill["slug"] = aliases[skill["slug"]]
                    skill["prerequisites"] = [aliases.get(p, p) for p in skill["prerequisites"]]
                for obj in mapped["learning_objects"]:
                    obj["skill"] = aliases.get(obj["skill"], obj["skill"])
                for assessment in mapped["assessments"]:
                    assessment["skill"] = aliases.get(assessment["skill"], assessment["skill"])
                problems = curriculum.selection_problems(
                    payload.selection
                ) + await curriculum.validate_private_payload(db, mapped, learner_id=learner_id)
                if any(p.level == "error" for p in problems):
                    raise ValueError("Lesson payload failed curriculum validation")
                row = LessonActivation(
                    learner_id=learner_id,
                    promotion_id=promotion.id,
                    request_key=request_key,
                    fingerprint=fingerprint,
                    draft_version=draft.version,
                    payload_sha256=command.payload_sha256,
                    payload_json=frozen,
                    binding_json=promotion.binding_json,
                )
                db.add(row)
                await db.flush()
                for skill in payload.skills:
                    db.add(
                        SkillNode(
                            id=ids[skill.slug],
                            slug=aliases[skill.slug],
                            owner_learner_id=learner_id,
                            domain=payload.domain,
                            title=skill.title,
                            description=skill.description,
                            success_criteria_json=skill.success_criteria,
                            assessment_requirements_json=skill.assessment_requirements,
                            example_applications_json=skill.example_applications,
                        )
                    )
                await db.flush()
                for identity in ids.values():
                    db.add(
                        LessonActivationSkill(
                            learner_id=learner_id, activation_id=row.id, entity_id=identity
                        )
                    )
                await db.flush()
                for obj in payload.learning_objects:
                    entity = LearningObject(
                        skill_id=ids[obj.skill],
                        version=1,
                        concept=obj.concept,
                        goal=obj.goal,
                        examples_json=obj.examples,
                        exercises_json=obj.exercises,
                        success_criteria_json=obj.success_criteria,
                        sources_json=obj.sources,
                    )
                    db.add(entity)
                    await db.flush()
                    db.add(
                        LessonActivationObject(
                            learner_id=learner_id, activation_id=row.id, entity_id=entity.id
                        )
                    )
                for assessment in payload.assessments:
                    rubric_id = None
                    if assessment.rubric:
                        rubric = AssessmentRubric(criteria_json=assessment.rubric, version=1)
                        db.add(rubric)
                        await db.flush()
                        rubric_id = rubric.id
                    item = dict(assessment.item)
                    item["draft_id"] = draft.id
                    if assessment.source_chunk_id:
                        item["source_chunk_id"] = assessment.source_chunk_id
                    test = Assessment(
                        skill_id=ids[assessment.skill],
                        owner_learner_id=learner_id,
                        kind=assessment.kind,
                        item_json=item,
                        rubric_id=rubric_id,
                    )
                    db.add(test)
                    await db.flush()
                    db.add(
                        LessonActivationAssessment(
                            learner_id=learner_id, activation_id=row.id, entity_id=test.id
                        )
                    )
                for skill in payload.skills:
                    for prerequisite in dict.fromkeys(skill.prerequisites):
                        parent = ids.get(prerequisite)
                        if parent is None:
                            parent = await db.scalar(
                                select(SkillNode.id).where(
                                    SkillNode.slug == prerequisite, skill_visible(learner_id)
                                )
                            )
                        if parent is None:
                            raise conflict("A prerequisite is unavailable.")
                        edge = SkillEdge(
                            from_skill_id=parent, to_skill_id=ids[skill.slug], kind="prerequisite"
                        )
                        db.add(edge)
                        await db.flush()
                        db.add(
                            LessonActivationEdge(
                                learner_id=learner_id, activation_id=row.id, entity_id=edge.id
                            )
                        )
                draft.status = "published"
                draft.version += 1
                draft.published_at = utcnow_iso()
                draft.validation_json = curriculum.problems_json(problems)
                await db.flush()
                receipt = await _receipt(db, row)
                await db.commit()
                return receipt
            except BaseException:
                await db.rollback()
                raise
