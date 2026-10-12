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
from app.schemas.task_reviews import TaskReviewCommand, TaskReviewReceipt

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
