"""Explicit correction transaction. Caller commits/rolls back; no automatic publication.

Not exposed through an HTTP route until confirmation/recovery UI acceptance.
"""

import copy
import hmac

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow_iso
from app.db.models import (
    Assessment,
    AssessmentRubric,
    QuestionCorrectionCommand,
    QuestionFeedback,
    QuestionReplacement,
    QuestionState,
)
from app.kernel import correction_drafts, correction_impact, question_replacements, question_state
from app.schemas.correction_drafts import CorrectionDraftReceipt, PublishCorrectionDraft


async def publish(
    db: AsyncSession, learner_id: str, draft_id: str, body: PublishCorrectionDraft
) -> CorrectionDraftReceipt:
    request = {"action": "publish", "draft_id": draft_id, **body.model_dump(mode="json")}
    prior = await correction_drafts._begin(db, learner_id, str(body.request_id), request)
    if prior is not None:
        return prior
    draft = await correction_drafts.get(db, learner_id, draft_id)
    if draft.status != "draft" or draft.revision != body.expected_revision:
        raise AppError("correction_draft_conflict", "This draft changed. Review it again.", 409)
    preview = await correction_impact.preview(db, learner_id, draft_id)
    if not hmac.compare_digest(preview.preview_token, body.preview_token):
        raise AppError(
            "correction_preview_conflict", "The impact changed. Refresh the preview.", 409
        )
    review = preview.review
    if (
        review.problems
        or review.content_changed
        or review.question_state_changed
        or review.source_status != "unchanged"
    ):
        raise AppError(
            "correction_not_ready", "Resolve the content, source or validation checks first.", 409
        )
    if draft.feedback_id:
        report = await db.get(QuestionFeedback, draft.feedback_id, populate_existing=True)
        expected = {key: draft.original_json[key] for key in ("kind", "item", "skill_id")}
        if (
            report is None
            or report.learner_id != learner_id
            or report.assessment_id != draft.assessment_id
            or report.withdrawn_at
            or report.snapshot_json != expected
        ):
            raise AppError("correction_report_conflict", "The originating report changed.", 409)
    original = await question_state.require_visible(db, learner_id, draft.assessment_id)
    if original.kind == "code" or "listening" in original.item_json:
        raise AppError(
            "correction_kind_unavailable",
            "Code and listening corrections require additional verification before publication.",
            409,
        )
    state = await question_state.read(db, learner_id, original.id)
    if state.state not in {"active", "suspended"}:
        raise AppError(
            "correction_state_unavailable",
            "This question is already replaced or retired.",
            409,
        )
    if draft.candidate_json == {
        "item": draft.original_json["item"],
        "rubric": draft.original_json["rubric"],
    }:
        raise AppError("correction_unchanged", "There are no question changes to publish.", 409)
    rubric = draft.candidate_json["rubric"]
    rubric_id = None
    if rubric is not None:
        row = AssessmentRubric(criteria_json=copy.deepcopy(rubric), version=1)
        db.add(row)
        await db.flush()
        rubric_id = row.id
    replacement = Assessment(
        owner_learner_id=learner_id,
        skill_id=original.skill_id,
        kind=original.kind,
        item_json=copy.deepcopy(draft.candidate_json["item"]),
        rubric_id=rubric_id,
    )
    db.add(replacement)
    await db.flush()
    current = await db.get(QuestionState, (learner_id, original.id))
    if current is None:
        current = QuestionState(learner_id=learner_id, assessment_id=original.id)
        db.add(current)
    current.state = "superseded"
    current.revision = state.revision + 1
    current.reason = "Explicitly published correction"
    current.updated_at = utcnow_iso()
    db.add(
        QuestionReplacement(
            learner_id=learner_id, original_id=original.id, replacement_id=replacement.id
        )
    )
    await db.flush()
    # Includes bounded ancestry validation after extension; a failure rolls back all writes.
    await question_replacements.selected(db, learner_id, replacement)
    draft.status = "published"
    draft.revision += 1
    draft.updated_at = utcnow_iso()
    result = CorrectionDraftReceipt(
        draft_id=draft.id,
        revision=draft.revision,
        status=draft.status,
        replacement_id=replacement.id,
    )
    db.add(
        QuestionCorrectionCommand(
            learner_id=learner_id,
            request_id=str(body.request_id),
            draft_id=draft.id,
            request_json=request,
            result_json=result.model_dump(),
        )
    )
    await db.flush()
    return result
