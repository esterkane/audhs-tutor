"""Explicit private start/status/stop; GET never dispatches model work."""

import json
from typing import Annotated

from fastapi import APIRouter, Header, Query, Request
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.authored_visuals import ReadDB, bounded_body
from app.api.deps import BudgetDep, Learner
from app.core.errors import AppError
from app.db.models import AuthoredVisualVersion, VisualGenerationRequest
from app.kernel.visual_generation import GenerationRequests, owned
from app.orchestrator.visual_generation import PROMPT_VERSION
from app.schemas.visual_generation import StartVisualGeneration, VisualGenerationStatus

router = APIRouter(prefix="/visual-generation", tags=["authored-visuals"])


async def status(db: AsyncSession, owner: str, identity: str) -> VisualGenerationStatus:
    row = await owned(db, owner, identity)
    document_id = None
    if row.result_version_id:
        document_id = await db.scalar(
            select(AuthoredVisualVersion.document_id).where(
                AuthoredVisualVersion.id == row.result_version_id,
                AuthoredVisualVersion.learner_id == owner,
            )
        )
    return VisualGenerationStatus(
        id=row.id,
        answer_id=json.loads(row.binding_json)["answer_id"],
        state=row.state,
        attempts=row.attempts,
        attempt_limit=row.attempt_limit,
        document_id=document_id,
        result_version_id=row.result_version_id,
        error_code=row.error_code,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post(
    "",
    response_model=VisualGenerationStatus,
    status_code=202,
    summary="Explicitly start or recover an idempotent local visual request",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["binding"],
                        "additionalProperties": False,
                        "properties": {
                            "binding": {"$ref": "#/components/schemas/AnswerVisualBinding"}
                        },
                    }
                }
            },
        }
    },
)
async def start(
    request: Request,
    learner: Learner,
    budget: BudgetDep,
    request_id: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> VisualGenerationStatus:
    if request.app.state.visual_jobs.closing:
        raise AppError("visual_shutdown", "Server is stopping. Try again after restart.", 503)
    try:
        body = StartVisualGeneration.model_validate_json(await bounded_body(request))
        # Prompt upgrades must not change the identity of an already accepted intent.
        # The original fingerprint still checks exact binding and attempt budget.
        async with request.app.state.session_factory() as db:
            prior_prompt = await db.scalar(
                select(VisualGenerationRequest.prompt_version).where(
                    VisualGenerationRequest.learner_id == learner.id,
                    VisualGenerationRequest.request_key == request_id,
                )
            )
        row = await GenerationRequests(request.app.state.session_factory).reserve(
            learner.id,
            request_id,
            body.binding,
            prior_prompt or PROMPT_VERSION,
        )
    except (ValidationError, ValueError):
        raise AppError("invalid_visual_request", "Invalid visual request or target.", 422) from None
    if row.state == "pending":
        request.app.state.visual_jobs.start(learner.id, row.id, budget)
    async with request.app.state.session_factory() as db:
        return await status(db, learner.id, row.id)


@router.get(
    "",
    response_model=list[VisualGenerationStatus],
    summary="Find recent requests for an owned saved answer without generating",
)
async def list_requests(
    db: ReadDB,
    learner: Learner,
    answer_id: Annotated[str, Query(min_length=1, max_length=128)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[VisualGenerationStatus]:
    ids = await db.scalars(
        select(VisualGenerationRequest.id)
        .where(
            VisualGenerationRequest.learner_id == learner.id,
            func.json_extract(VisualGenerationRequest.binding_json, "$.answer_id") == answer_id,
        )
        .order_by(VisualGenerationRequest.created_at.desc(), VisualGenerationRequest.id.desc())
        .limit(limit)
    )
    return [await status(db, learner.id, identity) for identity in ids]


@router.get(
    "/{identity}",
    response_model=VisualGenerationStatus,
    summary="Read owned visual request status without restarting work",
)
async def get_status(identity: str, db: ReadDB, learner: Learner) -> VisualGenerationStatus:
    return await status(db, learner.id, identity)


@router.post(
    "/{identity}/cancel",
    response_model=VisualGenerationStatus,
    summary="Stop visual generation without deleting an already saved result",
)
async def cancel(identity: str, request: Request, learner: Learner) -> VisualGenerationStatus:
    row = await GenerationRequests(request.app.state.session_factory).cancel(learner.id, identity)
    if row.state == "cancelled":
        request.app.state.visual_jobs.stop(learner.id, identity)
    async with request.app.state.session_factory() as db:
        return await status(db, learner.id, identity)
