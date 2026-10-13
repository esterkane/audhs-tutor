"""Explicit private draft preparation; local single-owner boundary, no inference."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Request
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Learner
from app.core.errors import AppError
from app.kernel.answer_lesson_binding import resolve_lesson_binding
from app.kernel.lesson_promotion import MAX_COMMAND_BYTES, LessonPromotionRepository
from app.schemas.lesson_promotion import LessonDraftPreview, LessonDraftReceipt

router = APIRouter(prefix="/lesson-promotions", tags=["lesson-promotions"])


async def read_snapshot(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as db:
        await db.execute(text("BEGIN"))
        try:
            yield db
        finally:
            await db.rollback()


@router.get(
    "/answers/{answer_id}/preview",
    response_model=LessonDraftPreview,
    summary="Preview private lesson source identity without creating a draft",
)
async def preview(
    answer_id: Annotated[str, Path(min_length=1, max_length=128)],
    db: Annotated[AsyncSession, Depends(read_snapshot)],
    learner: Learner,
) -> LessonDraftPreview:
    try:
        target = await resolve_lesson_binding(db, learner.id, answer_id)
    except KeyError:
        raise AppError("not_found", "Saved answer unavailable.", 404) from None
    except ValueError:
        raise AppError(
            "promotion_preview_unavailable", "Answer history cannot be prepared.", 409
        ) from None
    return LessonDraftPreview.model_validate(
        {"binding": target.binding, "grounding": target.grounding, "issues": target.issues}
    )


@router.post(
    "/drafts",
    response_model=LessonDraftReceipt,
    summary="Explicitly create an inactive private lesson draft from a saved answer",
    openapi_extra={
        "requestBody": {
            "required": True,
            "description": "Strict CreateLessonDraft command; 65536 streamed bytes maximum.",
            "content": {"application/json": {"schema": {"type": "object"}}},
        }
    },
)
async def create(
    request: Request,
    learner: Learner,
    request_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> LessonDraftReceipt:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_COMMAND_BYTES:
            raise AppError("promotion_too_large", "Lesson draft command exceeds size limit.", 413)
        body.extend(chunk)
    try:
        return await LessonPromotionRepository(request.app.state.session_factory).create(
            learner.id, request_key, bytes(body)
        )
    except KeyError:
        raise AppError("not_found", "Saved answer unavailable.", 404) from None
    except (ValidationError, ValueError):
        # Validation messages may contain private rejected input.
        raise AppError(
            "invalid_promotion", "Invalid lesson draft command or request identity.", 422
        ) from None
