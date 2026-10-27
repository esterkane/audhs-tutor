"""Read-only preparation for private lesson drafts. No inference or curriculum writes.

Reuses the bounded owned-answer resolver. A successful comparison certifies identity
only, not accuracy, ownership, lesson quality, or eligibility for shared publication.
"""

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TutorAnswer
from app.kernel.answer_visual_binding import resolve_answer_binding
from app.kernel.learning_scope import require_current_material
from app.schemas.answer_lesson_binding import AnswerLessonBinding


@dataclass(frozen=True)
class AnswerLessonResolution:
    binding: AnswerLessonBinding
    # Private server data: never a public API payload or a caller-supplied provenance claim.
    snapshot_json: str
    source_state_json: str
    issues: tuple[str, ...]
    grounding: str


async def resolve_lesson_binding(
    db: AsyncSession, learner_id: str, answer_id: str
) -> AnswerLessonResolution:
    resolved = await resolve_answer_binding(db, learner_id, answer_id)
    created_at = await db.scalar(
        select(TutorAnswer.created_at).where(
            TutorAnswer.id == answer_id, TutorAnswer.learner_id == learner_id
        )
    )
    if created_at is not None:
        await require_current_material(db, learner_id, created_at)
    checks = {
        identity: {
            "omitted": check.omitted,
            "sources": sorted(
                (source.model_dump(mode="json") for source in check.sources),
                key=lambda source: str(source["chunk_id"]),
            ),
        }
        for identity, check in resolved.source_checks.items()
    }
    state = json.dumps(checks, sort_keys=True, separators=(",", ":"), allow_nan=False)
    binding = AnswerLessonBinding(
        answer_id=resolved.binding.answer_id,
        question_sha256=resolved.binding.question_sha256,
        answer_sha256=resolved.binding.answer_sha256,
        lineage_sha256=resolved.binding.lineage_sha256,
        source_state_sha256=hashlib.sha256(state.encode("utf-8")).hexdigest(),
    )
    return AnswerLessonResolution(
        binding, resolved.snapshot_json, state, resolved.issues, resolved.grounding
    )


async def validate_lesson_binding(
    db: AsyncSession, learner_id: str, binding: AnswerLessonBinding
) -> AnswerLessonResolution:
    """Re-resolve owned state; caller must do so inside its eventual write transaction."""
    current = await resolve_lesson_binding(db, learner_id, binding.answer_id)
    if current.binding != binding:
        raise ValueError("Answer, lineage or source state changed")
    return current
