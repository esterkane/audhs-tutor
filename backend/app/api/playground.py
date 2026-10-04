from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, Request

from app.api.answer_jobs import schedule_index
from app.api.deps import DB, Gateway, Learner, SettingsDep
from app.db import workspace_requests
from app.orchestrator import playground
from app.schemas.playground import PlaygroundReply, PlaygroundRequest

router = APIRouter(prefix="/playground", tags=["playground"])


@router.post(
    "/tutor",
    summary="Explain, hint or discuss a bounded coding workspace",
    response_model=PlaygroundReply,
)
async def tutor(
    body: PlaygroundRequest,
    db: DB,
    learner: Learner,
    gateway: Gateway,
    settings: SettingsDep,
    request: Request,
    background: BackgroundTasks,
    idempotency_key: Annotated[UUID | None, Header()] = None,
) -> PlaygroundReply:
    learner_id = learner.id

    async def validate_origin() -> None:
        await playground.validate_lesson_origin(db, learner_id, body)

    identity = None
    if idempotency_key is not None:
        identity, saved = await workspace_requests.claim(
            db,
            learner_id,
            body.session_id,
            str(idempotency_key),
            body.model_dump(mode="json"),
            validate_new=validate_origin if body.lesson_origin else None,
        )
        if saved is not None:
            return PlaygroundReply.model_validate(saved)
    reply = await playground.respond(
        db, gateway, learner_id, body, settings=settings, recovery=request.app.state.answer_recovery
    )
    if identity is not None:
        await workspace_requests.complete(db, learner_id, identity, reply.model_dump(mode="json"))
    if reply.answer_id and not reply.reused:
        schedule_index(request, background, settings, learner_id)
    return reply
