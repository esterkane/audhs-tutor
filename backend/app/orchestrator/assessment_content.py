"""Opaque process-bound content tokens; no hidden answers are exposed in public digests."""

import copy
import hashlib
import hmac
import json
import secrets
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import Assessment, AssessmentRubric

_KEY = secrets.token_bytes(32)  # Restart invalidates displayed content, never completed replay.


async def snapshot(db: AsyncSession, assessment_id: str) -> dict[str, Any]:
    row = (
        (
            await db.execute(
                select(
                    Assessment.id,
                    Assessment.skill_id,
                    Assessment.kind,
                    Assessment.item_json,
                    Assessment.rubric_id,
                    AssessmentRubric.version,
                    AssessmentRubric.criteria_json,
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
    return copy.deepcopy(dict(row))


def token(content: dict[str, Any]) -> str:
    payload = json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return "ac1." + hmac.new(_KEY, payload.encode(), hashlib.sha256).hexdigest()


async def validate_new(db: AsyncSession, assessment_id: str, supplied: str | None) -> None:
    if not supplied:
        raise AppError(
            "assessment_content_required",
            "Reload this question before submitting. Your answer is retained.",
            409,
        )
    if not hmac.compare_digest(token(await snapshot(db, assessment_id)), supplied):
        raise AppError(
            "assessment_content_changed",
            "This question or grading criteria changed. Reload it and review your retained answer before submitting.",
            409,
        )


async def guard_write(db: AsyncSession, assessment_id: str, expected: dict[str, Any]) -> None:
    # SQLite's write lock serializes this check with all content writers until grading commits.
    await db.execute(
        update(Assessment).where(Assessment.id == assessment_id).values(kind=Assessment.kind)
    )
    current = await snapshot(db, assessment_id)
    if current != expected:
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
