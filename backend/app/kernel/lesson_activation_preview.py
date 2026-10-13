"""Read-only activation preview; callers hold a database read snapshot."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import CurriculumDraft, LessonActivation, LessonPromotion
from app.kernel.answer_lesson_binding import validate_lesson_binding
from app.kernel.lesson_activation import (
    MAX_PAYLOAD_BYTES,
    _receipt,
    canonical_payload,
    payload_digest,
    prepare_payload,
)
from app.schemas.answer_lesson_binding import AnswerLessonBinding
from app.schemas.lesson_activation import ActivateLesson, LessonActivationPreview


async def preview(db: AsyncSession, learner_id: str, draft_id: str) -> LessonActivationPreview:
    pair = (
        await db.execute(
            select(CurriculumDraft, LessonPromotion)
            .join(LessonPromotion, LessonPromotion.draft_id == CurriculumDraft.id)
            .where(
                CurriculumDraft.id == draft_id,
                CurriculumDraft.learner_id == learner_id,
                LessonPromotion.learner_id == learner_id,
            )
        )
    ).one_or_none()
    if pair is None:
        raise AppError("not_found", "Private lesson draft not found.", 404)
    draft, promotion = pair
    activated = await db.scalar(
        select(LessonActivation).where(
            LessonActivation.promotion_id == promotion.id, LessonActivation.learner_id == learner_id
        )
    )
    common = dict(
        draft_id=draft.id,
        promotion_id=promotion.id,
        draft_version=draft.version,
        title=draft.title,
        status=draft.status,
    )
    if activated is not None:
        return LessonActivationPreview(**common, receipt=await _receipt(db, activated))
    issues: list[str] = []
    warnings = [
        "Private lesson only. Activation does not verify facts, review an assessment, or award learning evidence."
    ]
    if draft.status != "draft":
        issues.append("Only an editable draft can be activated.")
    grounding = "unknown"
    try:
        binding = AnswerLessonBinding.model_validate_json(promotion.binding_json)
        source = await validate_lesson_binding(db, learner_id, binding)
        grounding = source.grounding
        warnings.extend(source.issues)
    except (KeyError, ValueError):
        issues.append("Answer or source history changed or is unavailable. Your draft is retained.")
    skills = objects = assessments = 0
    digest = None
    try:
        if len(canonical_payload(draft.payload_json).encode()) > MAX_PAYLOAD_BYTES:
            raise ValueError("oversized")
        payload, _, _, problems = await prepare_payload(db, learner_id, draft.payload_json)
        digest = payload_digest(draft.payload_json)
        skills, objects, assessments = (
            len(payload.skills),
            len(payload.learning_objects),
            len(payload.assessments),
        )
        warnings.extend(p.message for p in problems if p.level == "warning")
    except ValueError:
        issues.append(
            "Draft content needs correction before activation. Review its fields and prerequisites."
        )
    command = None
    if not issues and digest is not None:
        command = ActivateLesson(
            promotion_id=promotion.id, expected_version=draft.version, payload_sha256=digest
        )
    return LessonActivationPreview.model_validate(
        dict(
            **common,
            command=command,
            skills=skills,
            learning_objects=objects,
            assessments=assessments,
            warnings=tuple(dict.fromkeys(warnings)),
            issues=tuple(issues),
            grounding=grounding,
        )
    )
