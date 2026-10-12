"""Display-only reviewed-task evidence. Never changes scores or learning state."""

from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_versions import recovery_fingerprint
from app.core.errors import AppError
from app.db.models import AssessmentAttempt, AssessmentTaskReview
from app.kernel import task_reviews
from app.schemas.progress import ProgressReviewedResult


def all_criteria_passed(criteria: Any, results: Any) -> bool:
    if not isinstance(criteria, list) or not criteria or not isinstance(results, list):
        return False
    required = []
    for row in criteria:
        if not isinstance(row, dict) or not isinstance(row.get("criterion"), str):
            return False
        name = row["criterion"].strip().casefold()
        if not name or name in required:
            return False
        required.append(name)
    checked = []
    for row in results:
        if not isinstance(row, dict) or not isinstance(row.get("criterion"), str):
            return False
        name = row["criterion"].strip().casefold()
        if name in checked or row.get("passed") is not True:
            return False
        if not isinstance(row.get("evidence"), str) or not row["evidence"].strip():
            return False
        checked.append(name)
    return set(checked) == set(required)


async def reviewed_result(
    db: AsyncSession, learner_id: str, attempt: AssessmentAttempt
) -> ProgressReviewedResult | None:
    from app.kernel.progress import task_context

    context = task_context(attempt)
    if attempt.learner_id != learner_id or context is None:
        return None
    payloads = [
        value
        for value in (attempt.llm_result_json, attempt.deterministic_result_json)
        if isinstance(value, dict)
    ]
    if len(payloads) != 1:
        return None
    payload = payloads[0]
    binding = await task_reviews.restore_binding(
        db, learner_id, attempt.assessment_id, payload.get("task_review_binding")
    )
    if binding is None or binding.review is None:
        return None
    receipt = await db.get(AssessmentTaskReview, binding.review.receipt_id)
    if receipt is None or not isinstance(receipt.content_json, dict):
        return None
    if (
        task_reviews.fingerprint(receipt.content_json) != receipt.content_fingerprint
        or receipt.content_json.get("kind") != context.task_kind
        or receipt.content_json.get("rubric_version") != context.rubric_version
    ):
        return None
    try:
        task_reviews.require_reviewable(receipt.content_json)
    except (AppError, KeyError):
        return None
    source = receipt.content_json
    expected = {
        "id": source.get("assessment_id"),
        "skill_id": source.get("skill_id"),
        "kind": source.get("kind"),
        "item_json": source.get("item"),
        "rubric_id": source.get("rubric_id"),
        "version": source.get("rubric_version"),
        "criteria_json": source.get("criteria"),
    }
    if source.get("practice_revision"):
        expected["_question_state"] = source.get("practice_state")
        expected["_question_revision"] = source.get("practice_revision")
    if recovery_fingerprint(expected) != attempt.content_fingerprint:
        return None
    label: (
        Literal["Explanation check passed", "Application attempted", "Application check passed"]
        | None
    ) = None
    checked = attempt.grader_route in {"local", "hosted"} and all_criteria_passed(
        receipt.content_json.get("criteria"), payload.get("criterion_results")
    )
    if binding.review.facet == "application" and attempt.answer.strip():
        label = "Application check passed" if checked else "Application attempted"
    elif binding.review.facet == "explanation" and checked:
        label = "Explanation check passed"
    if label is None:
        return None
    try:
        current = await task_reviews.preview(db, learner_id, attempt.assessment_id)
        active = (
            task_reviews.fingerprint(current.content) == binding.review.content_fingerprint
            and current.approval_matches_content
            and current.reviewable
            and current.current_review is not None
            and current.current_review.facet == binding.review.facet
        )
    except AppError:
        active = False
    return ProgressReviewedResult(
        label=label,
        currently_eligible=active,
        exclusion_reason=None
        if active
        else "Task approval or content has changed since this attempt.",
        grading_method=attempt.grader_route,
    )
