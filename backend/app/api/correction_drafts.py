"""Explicit private authoring reads and repeat-safe saves. No publication route."""

from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import DB, Learner
from app.core.content_versions import token
from app.core.errors import AppError
from app.db.models import QuestionCorrectionCommand, QuestionCorrectionDraft
from app.kernel import correction_drafts, question_state
from app.schemas.correction_drafts import (
    CorrectionDraftList,
    CorrectionDraftReceipt,
    CorrectionDraftSummary,
    CorrectionDraftView,
    CorrectionSource,
    CreateCorrectionDraftRequest,
    DiscardCorrectionDraft,
    SaveCorrectionDraft,
)

router = APIRouter(prefix="/questions", tags=["question-authoring"])


def summary(row: QuestionCorrectionDraft) -> CorrectionDraftSummary:
    return CorrectionDraftSummary(
        id=row.id,
        assessment_id=row.assessment_id,
        revision=row.revision,
        status=row.status,
        kind=str(row.original_json.get("kind", "unknown")),
        updated_at=row.updated_at,
    )


@router.get(
    "/{assessment_id}/correction-source",
    response_model=CorrectionSource,
    summary="Enter question authoring: includes reference answers",
)
async def source(assessment_id: str, db: DB, learner: Learner) -> CorrectionSource:
    content = await correction_drafts.original(db, assessment_id, learner.id)
    state = await question_state.read(db, learner.id, assessment_id)
    return CorrectionSource(
        assessment_id=assessment_id,
        kind=content["kind"],
        candidate={"item": content["item"], "rubric": content["rubric"]},
        question_revision=state.revision,
        content_version=token({"content": content, "question_revision": state.revision}),
    )


@router.get("/correction-drafts", response_model=CorrectionDraftList)
async def listing(
    db: DB, learner: Learner, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)
) -> CorrectionDraftList:
    query = select(QuestionCorrectionDraft).where(QuestionCorrectionDraft.learner_id == learner.id)
    total = int(await db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = (
        await db.scalars(
            query.order_by(QuestionCorrectionDraft.updated_at.desc(), QuestionCorrectionDraft.id)
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return CorrectionDraftList(
        items=[summary(row) for row in rows], total=total, offset=offset, limit=limit
    )


@router.get(
    "/correction-drafts/{draft_id}",
    response_model=CorrectionDraftView,
    summary="Read your authoring draft, including reference answers",
)
async def read(draft_id: str, db: DB, learner: Learner) -> CorrectionDraftView:
    row = await correction_drafts.get(db, learner.id, draft_id)
    return CorrectionDraftView(
        **summary(row).model_dump(),
        candidate=row.candidate_json,
        original_candidate={
            "item": row.original_json["item"],
            "rubric": row.original_json["rubric"],
        },
        rationale=row.rationale,
        review=await correction_drafts.inspect(db, learner.id, draft_id),
    )


@router.get(
    "/correction-commands/{request_id}",
    response_model=CorrectionDraftReceipt,
    summary="Recover an acknowledged draft command without resending it",
)
async def receipt(request_id: UUID, db: DB, learner: Learner) -> CorrectionDraftReceipt:
    row = await db.get(QuestionCorrectionCommand, (learner.id, str(request_id)))
    if row is None:
        # A request may still be in flight. Absence is not evidence that retry with a NEW ID is safe.
        raise AppError(
            "correction_receipt_unavailable",
            "No committed receipt is visible. The request may still be running; retain its action ID.",
            404,
        )
    return CorrectionDraftReceipt.model_validate(row.result_json)


@router.post("/correction-drafts", response_model=CorrectionDraftReceipt)
async def create(
    body: CreateCorrectionDraftRequest, db: DB, learner: Learner
) -> CorrectionDraftReceipt:
    learner_id = learner.id
    await db.commit()
    try:
        result = await correction_drafts.create(db, learner_id, body)
        await db.commit()
        return result
    except BaseException:
        await db.rollback()
        raise


@router.put(
    "/correction-drafts/{draft_id}",
    response_model=CorrectionDraftReceipt,
    summary="Save draft work, including incomplete work; does not publish",
)
async def save(
    draft_id: str, body: SaveCorrectionDraft, db: DB, learner: Learner
) -> CorrectionDraftReceipt:
    learner_id = learner.id
    await db.commit()
    try:
        result = await correction_drafts.change(db, learner_id, draft_id, body)
        await db.commit()
        return result
    except BaseException:
        await db.rollback()
        raise


@router.post("/correction-drafts/{draft_id}/discard", response_model=CorrectionDraftReceipt)
async def discard(
    draft_id: str, body: DiscardCorrectionDraft, db: DB, learner: Learner
) -> CorrectionDraftReceipt:
    learner_id = learner.id
    await db.commit()
    try:
        result = await correction_drafts.change(db, learner_id, draft_id, body)
        await db.commit()
        return result
    except BaseException:
        await db.rollback()
        raise
