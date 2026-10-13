"""Explicit private activation transport; local single-owner access, no inference."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Request
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Learner
from app.core.errors import AppError
from app.kernel.lesson_activation import MAX_COMMAND_BYTES, LessonActivationRepository
from app.kernel.lesson_activation_preview import preview
from app.schemas.lesson_activation import LessonActivationPreview, LessonActivationReceipt

router = APIRouter(prefix="/lesson-activations", tags=["lesson-activations"])
Identity = Annotated[str, Path(min_length=1, max_length=128)]


async def read_snapshot(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as db:
        await db.execute(text("BEGIN"))
        try:
            yield db
        finally:
            await db.rollback()


@router.get(
    "/drafts/{draft_id}/preview",
    response_model=LessonActivationPreview,
    summary="Preview exact private draft activation without changing learning state",
)
async def activation_preview(
    draft_id: Identity, learner: Learner, db: Annotated[AsyncSession, Depends(read_snapshot)]
) -> LessonActivationPreview:
    return await preview(db, learner.id, draft_id)


@router.get(
    "/{activation_id}",
    response_model=LessonActivationReceipt,
    summary="Read an owned private lesson activation receipt",
)
async def receipt(
    activation_id: Identity, request: Request, learner: Learner
) -> LessonActivationReceipt:
    return await LessonActivationRepository(request.app.state.session_factory).get(
        learner.id, activation_id
    )


@router.post(
    "/commands",
    response_model=LessonActivationReceipt,
    summary="Explicitly activate one exact private lesson draft version",
    openapi_extra={
        "requestBody": {
            "required": True,
            "description": "Strict ActivateLesson command, limited to 4096 streamed bytes.",
            "content": {"application/json": {"schema": {"type": "object"}}},
        }
    },
)
async def activate(
    request: Request,
    learner: Learner,
    request_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> LessonActivationReceipt:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_COMMAND_BYTES:
            raise AppError("activation_too_large", "Activation request exceeds size limit.", 413)
        body.extend(chunk)
    try:
        return await LessonActivationRepository(request.app.state.session_factory).activate(
            learner.id, request_key, bytes(body)
        )
    except (ValidationError, ValueError):
        raise AppError(
            "invalid_activation", "Invalid activation request or draft content.", 422
        ) from None
