"""Atomic private draft creation. No model call, activation, evidence or permission upgrade."""

import hashlib
import json

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.base import new_id
from app.db.models import CurriculumDraft, LessonPromotion, LessonPromotionSnapshot
from app.kernel import curriculum
from app.kernel.answer_lesson_binding import validate_lesson_binding
from app.schemas.curriculum import DraftPayload
from app.schemas.lesson_promotion import CreateLessonDraft, LessonDraftReceipt

MAX_COMMAND_BYTES = 65536


class LessonPromotionRepository:
    def __init__(self, factory: async_sessionmaker[AsyncSession]):
        self.factory = factory

    async def create(self, learner_id: str, request_key: str, raw: bytes) -> LessonDraftReceipt:
        if not request_key.strip() or len(request_key) > 128:
            raise ValueError("Provide a request identity of at most 128 characters")
        if len(raw) > MAX_COMMAND_BYTES:
            raise ValueError("Lesson draft command exceeds size limit")
        command = CreateLessonDraft.model_validate_json(raw)
        canonical = json.dumps(command.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
        async with self.factory() as db:
            try:
                await db.execute(text("BEGIN IMMEDIATE"))
                prior = await db.scalar(
                    select(LessonPromotion).where(
                        LessonPromotion.learner_id == learner_id,
                        LessonPromotion.request_key == request_key,
                    )
                )
                if prior is not None:
                    if prior.fingerprint != fingerprint:
                        raise AppError(
                            "promotion_conflict",
                            "Request identity already used for different content.",
                            409,
                        )
                    receipt = LessonDraftReceipt(draft_id=prior.draft_id, promotion_id=prior.id)
                    await db.rollback()
                    return receipt
                # No external await/inference. Resolution and writes share this reservation.
                try:
                    target = await validate_lesson_binding(db, learner_id, command.binding)
                except ValueError:
                    raise AppError(
                        "promotion_target_changed",
                        "Answer or source history changed. Preview again.",
                        409,
                    ) from None
                draft_id, promotion_id = new_id(), new_id()
                slug = f"private-answer-{promotion_id.lower()}"
                payload = DraftPayload.model_validate(
                    {
                        "domain": command.domain.value,
                        "area_title": command.title,
                        "skills": [
                            {
                                "slug": slug,
                                "title": command.title,
                                "description": command.objective,
                                "prerequisites": list(command.prerequisites),
                                "success_criteria": list(command.criteria),
                                "assessment_requirements": {"dimensions": ["transfer"]},
                            }
                        ],
                        "learning_objects": [
                            {
                                "skill": slug,
                                "concept": command.title,
                                "goal": command.objective,
                                "examples": [command.explanation, command.worked_example],
                                "exercises": [command.question],
                                "success_criteria": list(command.criteria),
                                "sources": [],
                            }
                        ],
                        "assessments": [
                            {
                                "skill": slug,
                                "kind": "transfer",
                                "item": {"prompt": command.question},
                                "rubric": [{"criterion": c} for c in command.criteria],
                                "origin": "answer_derived",
                                "auto": False,
                                "guessable": False,
                            }
                        ],
                    }
                ).model_dump(mode="json")
                problems = await curriculum.validate_payload(db, payload)
                if any(p.level == "error" for p in problems):
                    raise ValueError("Lesson draft content failed curriculum validation")
                # Raw lineage is retained separately; do not invent passage grounding for edits.
                problems.append(
                    curriculum.Problem(
                        "warning",
                        "draft",
                        "Private answer-derived draft; source history is retained but not independently verified. "
                        "Activation is unavailable until private lesson publication is supported.",
                    )
                )
                db.add(
                    CurriculumDraft(
                        id=draft_id,
                        learner_id=learner_id,
                        title=command.title,
                        course=None,
                        section=None,
                        status="draft",
                        origin="answer_derived",
                        payload_json=payload,
                        validation_json=curriculum.problems_json(problems),
                    )
                )
                await db.flush()
                db.add(
                    LessonPromotion(
                        id=promotion_id,
                        learner_id=learner_id,
                        draft_id=draft_id,
                        answer_id=command.binding.answer_id,
                        request_key=request_key,
                        fingerprint=fingerprint,
                        binding_json=command.binding.model_dump_json(),
                        source_state_json=target.source_state_json,
                    )
                )
                await db.flush()
                db.add(
                    LessonPromotionSnapshot(
                        learner_id=learner_id,
                        promotion_id=promotion_id,
                        snapshot_json=target.snapshot_json,
                    )
                )
                await db.commit()
                return LessonDraftReceipt(draft_id=draft_id, promotion_id=promotion_id)
            except BaseException:
                await db.rollback()
                raise
