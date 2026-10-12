"""Explicit review receipts. Caller owns transactions; no grading or scheduling writes.

Not yet connected to the UI or grading. A review is a learner's authoring decision,
not independent validation, and must never retroactively qualify a prior attempt.
"""

import copy
import hashlib
import hmac
import json
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_versions import token
from app.core.errors import AppError
from app.db.models import Assessment, AssessmentRubric, AssessmentTaskReview, SkillNode
from app.kernel import question_state
from app.schemas.task_reviews import (
    FrozenReviewIdentity,
    FrozenTaskReview,
    TaskReviewCommand,
    TaskReviewPreview,
    TaskReviewReceipt,
)

POLICY_VERSION = "task-review-v1"


async def snapshot(db: AsyncSession, learner_id: str, assessment_id: str) -> dict[str, Any]:
    assessment = await question_state.require_visible(db, learner_id, assessment_id)
    state = await question_state.read(db, learner_id, assessment_id)
    rubric = (
        await db.get(AssessmentRubric, assessment.rubric_id, populate_existing=True)
        if assessment.rubric_id
        else None
    )
    skill = await db.get(SkillNode, assessment.skill_id, populate_existing=True)
    if skill is None:
        raise AppError("task_review_unavailable", "The task objective is unavailable.", 409)
    return copy.deepcopy(
        {
            "assessment_id": assessment.id,
            "skill_id": skill.id,
            "kind": assessment.kind,
            "item": assessment.item_json,
            "rubric_id": assessment.rubric_id,
            "rubric_version": rubric.version if rubric else None,
            "criteria": rubric.criteria_json if rubric else None,
            "objective": {
                "title": skill.title,
                "description": skill.description,
                "success_criteria": skill.success_criteria_json,
                "assessment_requirements": skill.assessment_requirements_json,
                "example_applications": skill.example_applications_json,
            },
            "practice_state": state.state,
            "practice_revision": state.revision,
        }
    )


def fingerprint(content: dict[str, Any]) -> str:
    encoded = json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return "task-review-v1:" + hashlib.sha256(encoded.encode()).hexdigest()


async def latest(
    db: AsyncSession, learner_id: str, assessment_id: str
) -> AssessmentTaskReview | None:
    row: AssessmentTaskReview | None = await db.scalar(
        select(AssessmentTaskReview)
        .where(
            AssessmentTaskReview.learner_id == learner_id,
            AssessmentTaskReview.assessment_id == assessment_id,
        )
        .order_by(AssessmentTaskReview.revision.desc())
        .limit(1)
        .execution_options(populate_existing=True)
    )

    return row


def receipt(row: AssessmentTaskReview) -> TaskReviewReceipt:
    return TaskReviewReceipt.model_validate(
        {key: getattr(row, key) for key in TaskReviewReceipt.model_fields}
    )


def require_reviewable(content: dict[str, Any]) -> None:
    # Executable check provenance needs its own review; do not infer it from code runs.
    if content["kind"] not in {
        "explain_back",
        "transfer",
        "challenge_planted_error",
        "challenge_steelman",
        "challenge_teach_back",
        "challenge_calibration",
    }:
        raise AppError(
            "task_review_unsupported", "This task type does not support rubric review yet.", 409
        )
    criteria = content["criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise AppError("task_review_rubric_required", "Review requires a nonempty rubric.", 409)
    names = [
        c["criterion"].strip().casefold()
        if isinstance(c, dict) and isinstance(c.get("criterion"), str)
        else ""
        for c in criteria
    ]
    if not all(names) or len(set(names)) != len(names):
        raise AppError(
            "task_review_rubric_invalid", "Rubric criteria must be present and distinct.", 409
        )
    if content["practice_state"] != "active":
        raise AppError("task_review_inactive", "Only an active task can receive a new review.", 409)


async def decide(
    db: AsyncSession, learner_id: str, assessment_id: str, body: TaskReviewCommand
) -> TaskReviewReceipt:
    await db.execute(
        update(Assessment)
        .where(Assessment.id == assessment_id, question_state.visible(learner_id))
        .values(kind=Assessment.kind)
    )
    await question_state.require_visible(db, learner_id, assessment_id)
    request = {"assessment_id": assessment_id, **body.model_dump(mode="json")}
    prior = await db.scalar(
        select(AssessmentTaskReview).where(
            AssessmentTaskReview.learner_id == learner_id,
            AssessmentTaskReview.request_id == str(body.request_id),
        )
    )
    if prior is not None:
        if prior.request_json != request:
            raise AppError(
                "task_review_request_conflict", "This review action ID was already used.", 409
            )
        return receipt(prior)
    if not body.confirmed:
        raise AppError(
            "task_review_confirmation_required",
            "Explicit task/rubric review confirmation is required.",
            409,
        )
    current = await latest(db, learner_id, assessment_id)
    if body.expected_revision != (current.revision if current else 0):
        raise AppError("task_review_changed", "The review changed. Reload it before deciding.", 409)
    content = await snapshot(db, learner_id, assessment_id)
    if not hmac.compare_digest(body.content_version.encode(), token(content).encode()):
        raise AppError(
            "task_review_content_changed",
            "The task, objective or rubric changed. Review the current version.",
            409,
        )
    if body.decision == "approve":
        require_reviewable(content)
    elif current is None or current.decision != "approve" or current.facet != body.facet:
        raise AppError(
            "task_review_revoke_invalid", "There is no matching approved review to revoke.", 409
        )
    row = AssessmentTaskReview(
        learner_id=learner_id,
        assessment_id=assessment_id,
        request_id=str(body.request_id),
        request_json=request,
        revision=body.expected_revision + 1,
        decision=body.decision,
        facet=body.facet,
        content_json=copy.deepcopy(content),
        content_fingerprint=fingerprint(content),
        policy_version=POLICY_VERSION,
    )
    db.add(row)
    await db.flush()
    return receipt(row)


async def preview(db: AsyncSession, learner_id: str, assessment_id: str) -> TaskReviewPreview:
    content = await snapshot(db, learner_id, assessment_id)
    current = await latest(db, learner_id, assessment_id)
    reason = None
    try:
        require_reviewable(content)
    except AppError as error:
        reason = str(error)
    return TaskReviewPreview(
        assessment_id=assessment_id,
        content_version=token(content),
        content=content,
        current_review=receipt(current) if current else None,
        approval_matches_content=bool(
            current
            and current.decision == "approve"
            and current.policy_version == POLICY_VERSION
            and current.content_fingerprint == fingerprint(content)
        ),
        reviewable=reason is None,
        unavailable_reason=reason,
    )


async def capture(
    db: AsyncSession,
    learner_id: str,
    assessment_id: str,
    expected_content: dict[str, Any],
) -> FrozenTaskReview:
    """Capture under the caller's preparation write lock; never commit or qualify.

    The expected content is the separate review snapshot taken before inference,
    not the assessment recovery snapshot. Callers must preserve the latter's hash.
    """
    content = await snapshot(db, learner_id, assessment_id)
    if fingerprint(content) != fingerprint(expected_content):
        raise AppError(
            "task_review_content_changed",
            "The task, objective or rubric changed before preparation. Review it again.",
            409,
        )
    try:
        require_reviewable(content)
    except AppError:
        return FrozenTaskReview(review=None)
    current = await latest(db, learner_id, assessment_id)
    if (
        current is None
        or current.decision != "approve"
        or current.policy_version != POLICY_VERSION
        or current.content_fingerprint != fingerprint(content)
    ):
        return FrozenTaskReview(review=None)
    return FrozenTaskReview(
        review=FrozenReviewIdentity(
            receipt_id=current.id,
            assessment_id=assessment_id,
            revision=current.revision,
            facet=receipt(current).facet,
            policy_version="task-review-v1",
            content_fingerprint=current.content_fingerprint,
        )
    )


async def restore_binding(
    db: AsyncSession, learner_id: str, assessment_id: str, raw: Any
) -> FrozenTaskReview | None:
    """Validate saved authority; never replace it with today's review state."""
    from pydantic import ValidationError

    if not isinstance(raw, dict) or not {"schema_version", "review"} <= raw.keys():
        return None
    try:
        binding = FrozenTaskReview.model_validate(raw)
    except ValidationError:
        return None
    identity = binding.review
    if identity is None:
        return binding
    row = await db.get(AssessmentTaskReview, identity.receipt_id, populate_existing=True)
    if (
        row is None
        or row.learner_id != learner_id
        or row.assessment_id != assessment_id
        or identity.assessment_id != assessment_id
        or row.decision != "approve"
        or row.revision != identity.revision
        or row.facet != identity.facet
        or row.policy_version != identity.policy_version
        or row.content_fingerprint != identity.content_fingerprint
    ):
        return None
    return binding
