"""Private visual command transport; explicit requests never trigger inference."""

from typing import Annotated

from fastapi import APIRouter, Header, Request
from pydantic import ValidationError

from app.api.deps import Learner, SettingsDep
from app.core.errors import AppError
from app.kernel.authored_visuals import VisualRepository
from app.schemas.authored_visuals import VisualReceipt
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
