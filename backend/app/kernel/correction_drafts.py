"""Private draft storage only. No publication, selection, evidence or inference.

Callers commit or roll back. The learner-row write lock serializes receipts and
revision checks even when two requests attempt to create their first draft.
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
from app.db.base import utcnow_iso
from app.db.models import (
    AssessmentRubric,
    LearnerProfile,
    QuestionCorrectionCommand,
    QuestionCorrectionDraft,
    QuestionFeedback,
)
from app.kernel import correction_sources, correction_validation, question_state
from app.schemas.correction_drafts import (
    CorrectionDraftReceipt,
    CreateCorrectionDraft,
    DiscardCorrectionDraft,
    SaveCorrectionDraft,
)


def fingerprint(content: dict[str, Any]) -> str:
    """Server-private durable content identity, never a public answer digest."""
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "correction-original-v1:" + hashlib.sha256(canonical.encode()).hexdigest()


async def original(
    db: AsyncSession, assessment_id: str, learner_id: str | None = None
) -> dict[str, Any]:
    a = await question_state.require_visible(db, learner_id, assessment_id)
    rubric = (
        await db.get(AssessmentRubric, a.rubric_id, populate_existing=True) if a.rubric_id else None
    )
    return copy.deepcopy(
        {
            "assessment_id": a.id,
            "skill_id": a.skill_id,
            "kind": a.kind,
            "item": a.item_json,
            "rubric_id": a.rubric_id,
            "rubric_version": rubric.version if rubric else None,
            "rubric": rubric.criteria_json if rubric else None,
            "source_evidence": await correction_sources.capture(db, a.item_json),
        }
    )


async def get(db: AsyncSession, learner_id: str, draft_id: str) -> QuestionCorrectionDraft:
    row = await db.scalar(
        select(QuestionCorrectionDraft)
        .where(
            QuestionCorrectionDraft.id == draft_id,
            QuestionCorrectionDraft.learner_id == learner_id,
        )
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise AppError("not_found", "This correction draft is unavailable.", 404)
    return row


async def _begin(
    db: AsyncSession, learner_id: str, request_id: str, request: dict[str, Any]
) -> CorrectionDraftReceipt | None:
    await db.execute(
        update(LearnerProfile)
        .where(LearnerProfile.id == learner_id)
        .values(display_name=LearnerProfile.display_name)
    )
    if await db.get(LearnerProfile, learner_id) is None:
        raise AppError("not_found", "Learner unavailable.", 404)
    prior = await db.get(
        QuestionCorrectionCommand, (learner_id, request_id), populate_existing=True
    )
    if prior is None:
        return None
    if prior.request_json != request:
        raise AppError("correction_request_conflict", "This action ID was already used.", 409)
    return CorrectionDraftReceipt.model_validate(prior.result_json)


async def _record(
    db: AsyncSession,
    learner_id: str,
    request_id: str,
    request: dict[str, Any],
    draft: QuestionCorrectionDraft,
) -> CorrectionDraftReceipt:
    result = CorrectionDraftReceipt(draft_id=draft.id, revision=draft.revision, status=draft.status)
    db.add(
        QuestionCorrectionCommand(
            learner_id=learner_id,
            request_id=request_id,
            draft_id=draft.id,
            request_json=request,
            result_json=result.model_dump(),
        )
    )
    await db.flush()
    return result


async def create(
    db: AsyncSession, learner_id: str, body: CreateCorrectionDraft
) -> CorrectionDraftReceipt:
    request = {"action": "create", **body.model_dump(mode="json")}
    prior = await _begin(db, learner_id, str(body.request_id), request)
    if prior:
        return prior
    content = await original(db, body.assessment_id, learner_id)
    state = await question_state.read(db, learner_id, body.assessment_id)
    if state.revision != body.expected_question_revision:
        raise AppError("question_state_conflict", "Question status changed. Reload it.", 409)
    if body.expected_content_version is not None and not hmac.compare_digest(
        token({"content": content, "question_revision": state.revision}),
        body.expected_content_version,
    ):
        raise AppError(
            "correction_content_conflict",
            "Question content changed. Reload before creating a draft.",
            409,
        )
    if body.feedback_id:
        report = await db.get(QuestionFeedback, body.feedback_id, populate_existing=True)
        if (
            report is None
            or report.learner_id != learner_id
            or report.assessment_id != body.assessment_id
        ):
            raise AppError("not_found", "This question report is unavailable.", 404)
        # Never silently rebase a reported question onto different current content.
        reported = {
            "kind": content["kind"],
            "item": content["item"],
            "skill_id": content["skill_id"],
        }
        if report.withdrawn_at or reported != report.snapshot_json:
            raise AppError(
                "correction_report_conflict",
                "The report or question changed. Review it again.",
                409,
            )
    draft = QuestionCorrectionDraft(
        learner_id=learner_id,
        assessment_id=body.assessment_id,
        feedback_id=body.feedback_id,
        original_json=content,
        original_fingerprint=fingerprint(content),
        question_revision=state.revision,
        candidate_json=copy.deepcopy({"item": content["item"], "rubric": content["rubric"]}),
        revision=1,
        status="draft",
    )
    db.add(draft)
    await db.flush()
    return await _record(db, learner_id, str(body.request_id), request, draft)


async def change(
    db: AsyncSession,
    learner_id: str,
    draft_id: str,
    body: SaveCorrectionDraft | DiscardCorrectionDraft,
) -> CorrectionDraftReceipt:
    saving = isinstance(body, SaveCorrectionDraft)
    request = {
        "action": "save" if saving else "discard",
        "draft_id": draft_id,
        **body.model_dump(mode="json"),
    }
    prior = await _begin(db, learner_id, str(body.request_id), request)
    if prior:
        return prior
    draft = await get(db, learner_id, draft_id)
    if draft.revision != body.expected_revision or draft.status != "draft":
        raise AppError(
            "correction_draft_conflict", "This draft changed. Your edits are retained.", 409
        )
    if isinstance(body, SaveCorrectionDraft):
        # Candidate storage is deliberately not grading validation. It is never used by
        # selectors; typed adapters and source-version checks precede any editing API.
        draft.candidate_json = copy.deepcopy(body.candidate)
        draft.rationale = body.rationale
    else:
        draft.status = "discarded"
    draft.revision += 1
    draft.updated_at = utcnow_iso()
    return await _record(db, learner_id, str(body.request_id), request, draft)


async def inspect(db: AsyncSession, learner_id: str, draft_id: str) -> dict[str, Any]:
    """Internal review state, not authorization or a publication-ready result."""
    draft = await get(db, learner_id, draft_id)
    current = await original(db, draft.assessment_id, learner_id)
    baseline = draft.original_json
    state = await question_state.read(db, learner_id, draft.assessment_id)
    source_baseline = baseline.get("source_evidence")
    return {
        "problems": correction_validation.review(baseline, draft.candidate_json),
        "content_changed": {k: v for k, v in current.items() if k != "source_evidence"}
        != {k: v for k, v in baseline.items() if k != "source_evidence"},
        "question_state_changed": state.revision != draft.question_revision,
        "source_status": "not_captured"
        if source_baseline is None
        else "changed"
        if current["source_evidence"] != source_baseline
        else "incomplete"
        if not source_baseline.get("complete")
        else "unchanged",
        "draft_status": draft.status,
        "publication_available": False,
    }
