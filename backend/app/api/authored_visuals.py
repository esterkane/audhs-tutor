"""Private visual command transport; explicit requests never trigger inference."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Learner, SettingsDep
from app.core.errors import AppError
from app.kernel import visual_history
from app.kernel.authored_visuals import VisualRepository
from app.schemas.authored_visuals import VisualReceipt
from app.schemas.visual_history import (
    AnswerVisualTarget,
    VisualDocumentSummary,
    VisualReviewRecord,
    VisualVersionDetail,
    VisualVersionSummary,
)
from app.schemas.visual_relationship import MAX_RELATIONSHIP_BYTES

router = APIRouter(prefix="/authored-visuals", tags=["authored-visuals"])


async def bounded_body(request: Request) -> bytes:
    """Bound actual streamed bytes, including absent or dishonest Content-Length."""
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_RELATIONSHIP_BYTES:
            raise AppError("visual_too_large", "Visual command exceeds the size limit.", 413)
        body.extend(chunk)
    return bytes(body)


@router.post(
    "/commands",
    response_model=VisualReceipt,
    openapi_extra={
        "requestBody": {
            "required": True,
            "description": "Strict save/review/archive command; bounded to 131072 bytes before parsing.",
            "content": {"application/json": {"schema": {"type": "object"}}},
        }
    },
    summary="Explicitly save, review, archive or restore a private visual",
)
async def command(
    request: Request,
    learner: Learner,
    settings: SettingsDep,
    request_id: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> VisualReceipt:
    raw = await bounded_body(request)
    repository = VisualRepository(
        request.app.state.session_factory,
        quarantine_below_trust=settings.quarantine_below_trust,
    )
    try:
        return await repository.execute(learner.id, request_id, raw)
    except (ValidationError, ValueError):
        # Pydantic error strings include rejected input; never echo private content.
        raise AppError(
            "invalid_visual_command", "Invalid visual command or request identity.", 422
        ) from None


async def read_snapshot(request: Request) -> AsyncIterator[AsyncSession]:
    # A real SQLite read transaction keeps multi-query projections consistent.
    async with request.app.state.session_factory() as db:
        await db.execute(text("BEGIN"))
        try:
            yield db
        finally:
            await db.rollback()


ReadDB = Annotated[AsyncSession, Depends(read_snapshot)]
PageOffset = Annotated[int, Query(ge=0, le=1000000)]
PageLimit = Annotated[int, Query(ge=1, le=50)]


@router.get("", response_model=list[VisualDocumentSummary], summary="List private visual documents")
async def list_documents(
    db: ReadDB,
    learner: Learner,
    archived: bool = False,
    offset: PageOffset = 0,
    limit: PageLimit = 20,
) -> list[VisualDocumentSummary]:
    return await visual_history.documents(db, learner.id, archived, offset, limit)


@router.get(
    "/{document_id}",
    response_model=VisualDocumentSummary,
    summary="Read current visual document revision",
)
async def get_document(document_id: str, db: ReadDB, learner: Learner) -> VisualDocumentSummary:
    row = await visual_history.document(db, learner.id, document_id)
    return VisualDocumentSummary.model_validate(row, from_attributes=True)


@router.get(
    "/{document_id}/versions",
    response_model=list[VisualVersionSummary],
    summary="List immutable visual versions",
)
async def list_versions(
    document_id: str, db: ReadDB, learner: Learner, offset: PageOffset = 0, limit: PageLimit = 20
) -> list[VisualVersionSummary]:
    return await visual_history.versions(db, learner.id, document_id, offset, limit)


@router.get(
    "/{document_id}/versions/{version_id}",
    response_model=VisualVersionDetail,
    summary="Read a visual version and present grounding availability",
)
async def get_version(
    document_id: str, version_id: str, db: ReadDB, learner: Learner, settings: SettingsDep
) -> VisualVersionDetail:
    return await visual_history.detail(
        db, learner.id, document_id, version_id, settings.quarantine_below_trust
    )


@router.get(
    "/{document_id}/versions/{version_id}/reviews",
    response_model=list[VisualReviewRecord],
    summary="Read historical presentation reviews, not learning evidence",
)
async def list_reviews(
    document_id: str,
    version_id: str,
    db: ReadDB,
    learner: Learner,
    offset: PageOffset = 0,
    limit: PageLimit = 20,
) -> list[VisualReviewRecord]:
    return await visual_history.reviews(db, learner.id, document_id, version_id, offset, limit)


@router.get(
    "/answer-target/{answer_id}",
    response_model=AnswerVisualTarget,
    summary="Resolve exact owned Ask target before explicit visual creation",
)
async def get_answer_target(answer_id: str, db: ReadDB, learner: Learner) -> AnswerVisualTarget:
    return await visual_history.answer_target(db, learner.id, answer_id)
