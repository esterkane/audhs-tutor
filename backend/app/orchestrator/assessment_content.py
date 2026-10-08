"""Opaque process-bound content tokens; no hidden answers are exposed in public digests."""

import copy
import hashlib
import hmac
import json
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_versions import token as token
from app.core.errors import AppError
from app.db.models import Assessment, AssessmentRubric, QuestionState


def recovery_fingerprint(content: dict[str, Any]) -> str:
    """Private durable identity, never sent to clients as a content token.

    Public tokens intentionally expire on process restart. Recovery needs stable
    equality without copying the hidden answer/rubric into another private record.
    """
    payload = json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return "assessment-recovery-v1:" + hashlib.sha256(payload.encode()).hexdigest()


async def snapshot(
    db: AsyncSession, assessment_id: str, learner_id: str | None = None
) -> dict[str, Any]:
    row = (
        (
            await db.execute(
                select(
                    Assessment.id,
                    QuestionState.state.label("_question_state"),
                    QuestionState.revision.label("_question_revision"),
                    Assessment.skill_id,
                    Assessment.kind,
                    Assessment.item_json,
                    Assessment.rubric_id,
                    AssessmentRubric.version,
                    AssessmentRubric.criteria_json,
                )
                .outerjoin(
                    QuestionState,
                    and_(
                        QuestionState.assessment_id == Assessment.id,
                        QuestionState.learner_id == learner_id,
                    ),
                )
                .outerjoin(AssessmentRubric, Assessment.rubric_id == AssessmentRubric.id)
                .where(Assessment.id == assessment_id)
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AppError("not_found", "This assessment is unavailable.", 404)
    result = copy.deepcopy(dict(row))
    # Existing active questions retain their original durable recovery fingerprint.
    # Once an explicit decision exists, its revision binds every new view/submission.
    if result["_question_revision"] is None:
        result.pop("_question_state")
        result.pop("_question_revision")
    return result


def require_eligible(content: dict[str, Any]) -> None:
    if content.get("_question_state", "active") != "active":
        raise AppError(
            "assessment_unavailable",
            "This question is no longer available for practice. Your answer is retained.",
            409,
        )


async def validate_new(
    db: AsyncSession, assessment_id: str, supplied: str | None, learner_id: str | None = None
) -> None:
    if not supplied:
        raise AppError(
            "assessment_content_required",
            "Reload this question before submitting. Your answer is retained.",
            409,
        )
    content = await snapshot(db, assessment_id, learner_id)
    require_eligible(content)
    if not hmac.compare_digest(token(content), supplied):
        raise AppError(
            "assessment_content_changed",
            "This question or grading criteria changed. Reload it and review your retained answer before submitting.",
            409,
        )


async def guard_write(
    db: AsyncSession, assessment_id: str, expected: dict[str, Any], learner_id: str | None = None
) -> None:
    # SQLite's write lock serializes this check with all content writers until grading commits.
    await db.execute(
        update(Assessment).where(Assessment.id == assessment_id).values(kind=Assessment.kind)
    )
    current = await snapshot(db, assessment_id, learner_id)
    if current != expected or current.get("_question_state", "active") != "active":
        raise AppError(
            "assessment_content_changed_during_grading",
            "Content changed while grading. No learning evidence was saved. "
            "This request remains unresolved; do not submit it again automatically.",
            409,
        )


def assessment(content: dict[str, Any]) -> Assessment:
    """Detached immutable-by-convention grading inputs, never added to the session."""
    return Assessment(
        **{
            key: copy.deepcopy(content[key])
            for key in ("id", "skill_id", "kind", "item_json", "rubric_id")
        }
    )
