"""Explicit learner-scoped suspension foundation; no API or selector enabled yet.

The caller owns commit/rollback. A SQLite write lock serializes revision checks and
receipts. No model calls, learning events, attempts or scheduling state are changed.
"""

from sqlalchemy import exists, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import AppError
from app.db.base import utcnow_iso
from app.db.models import Assessment, QuestionState, QuestionTransition, ReviewItem
from app.schemas.question_state import QuestionStateOut, QuestionTransitionIn


def eligible(learner_id: str) -> ColumnElement[bool]:
    """Correlated Assessment predicate. Historical reads must not use this filter."""
    return ~exists().where(
        QuestionState.learner_id == learner_id,
        QuestionState.assessment_id == Assessment.id,
        QuestionState.state != "active",
    )


def review_reference() -> ColumnElement[str]:
    """Keep the same legacy ref fallback for filtering and displayed snapshots."""
    return func.coalesce(
        func.nullif(ReviewItem.prompt_json["assessment_id"].as_string(), ""),
        ReviewItem.prompt_json["ref"].as_string(),
    )


def review_eligible(learner_id: str) -> ColumnElement[bool]:
    """Vocabulary refs are not assessment IDs, even when their strings coincide."""
    return ~exists().where(
        QuestionState.learner_id == learner_id,
        QuestionState.assessment_id == review_reference(),
        QuestionState.state != "active",
        func.coalesce(ReviewItem.prompt_json["type"].as_string(), "") != "vocab",
    ).correlate(ReviewItem)


async def read(db: AsyncSession, learner_id: str, assessment_id: str) -> QuestionStateOut:
    if await db.get(Assessment, assessment_id) is None:
        raise AppError("not_found", "This question is unavailable.", 404)
    row = await db.get(QuestionState, (learner_id, assessment_id), populate_existing=True)
    if row is None:
        return QuestionStateOut(assessment_id=assessment_id, state="active", revision=0)
    return QuestionStateOut.model_validate(
        {
            "assessment_id": assessment_id,
            "state": row.state,
            "revision": row.revision,
            "reason": row.reason,
        }
    )


async def require_active(db: AsyncSession, learner_id: str, assessment_id: str) -> None:
    current = await read(db, learner_id, assessment_id)
    if current.state != "active":
        raise AppError(
            "assessment_unavailable",
            "This question is unavailable for practice. Choose another question or restore it.",
            409,
        )


async def transition(
    db: AsyncSession, learner_id: str, assessment_id: str, body: QuestionTransitionIn
) -> QuestionStateOut:
    # Acquire the SQLite write lock before reading receipt or revision. No earlier
    # transaction is committed here: rollback also removes this transition/receipt.
    await db.execute(
        update(Assessment).where(Assessment.id == assessment_id).values(kind=Assessment.kind)
    )
    request = {"assessment_id": assessment_id, **body.model_dump(mode="json")}
    key = (learner_id, str(body.request_id))
    prior = await db.get(QuestionTransition, key, populate_existing=True)
    if prior is not None:
        if prior.request_json != request:
            raise AppError("question_request_conflict", "This action ID was already used.", 409)
        return QuestionStateOut.model_validate(prior.result_json)
    current = await read(db, learner_id, assessment_id)
    if current.revision != body.expected_revision:
        raise AppError("question_state_conflict", "This question changed. Reload its status.", 409)
    required = "active" if body.action == "suspend" else "suspended"
    if current.state != required:
        raise AppError(
            "question_transition_invalid", "This action is unavailable in this state.", 409
        )
    result = QuestionStateOut(
        assessment_id=assessment_id,
        state="suspended" if body.action == "suspend" else "active",
        revision=current.revision + 1,
        reason=body.reason,
    )
    row = await db.get(QuestionState, (learner_id, assessment_id))
    if row is None:
        row = QuestionState(learner_id=learner_id, assessment_id=assessment_id)
        db.add(row)
    row.state, row.revision, row.reason = result.state, result.revision, result.reason
    row.updated_at = utcnow_iso()
    db.add(
        QuestionTransition(
            learner_id=learner_id,
            request_id=str(body.request_id),
            assessment_id=assessment_id,
            request_json=request,
            result_json=result.model_dump(mode="json"),
        )
    )
    await db.flush()
    return result
