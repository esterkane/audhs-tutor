"""Validate a revision root without grading or writing learning state.

Call before inference and again inside the eventual write transaction. This module
alone does not enable revision submissions or alter evidence policy.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import AssessmentAttempt
from app.kernel.session import get_owned
from app.orchestrator import assessment_content


async def validate_root(
    db: AsyncSession,
    *,
    learner_id: str,
    session_id: str,
    assessment_id: str,
    root_attempt_id: str,
) -> AssessmentAttempt:
    session = await get_owned(db, session_id, learner_id)
    await db.refresh(session, attribute_names=["ended_at"])
    if session.ended_at is not None:
        raise AppError("revision_session_ended", "Start a new session for further practice.", 409)
    root = await db.get(AssessmentAttempt, root_attempt_id, populate_existing=True)
    if (
        root is None
        or root.learner_id != learner_id
        or root.session_id != session_id
        or root.assessment_id != assessment_id
    ):
        raise AppError("revision_original_unavailable", "The original attempt is unavailable.", 404)
    if root.revision_of_attempt_id is not None:
        raise AppError(
            "revision_original_required", "Use the original attempt for this revision.", 409
        )
    content = await assessment_content.snapshot(db, assessment_id, learner_id)
    assessment_content.require_eligible(content)
    if root.content_fingerprint is None:
        raise AppError(
            "revision_original_unverified",
            "The original question version cannot be verified. Your answer is retained.",
            409,
        )
    if root.content_fingerprint != assessment_content.recovery_fingerprint(content):
        raise AppError(
            "revision_content_changed",
            "The question or rubric changed. Your original answer and feedback are retained.",
            409,
        )
    return root
