from fastapi import APIRouter, BackgroundTasks, Request

from app.api.answer_jobs import schedule_index
from app.api.deps import DB, Gateway, Learner, SettingsDep
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
) -> PlaygroundReply:
    learner_id = learner.id
    reply = await playground.respond(db, gateway, learner_id, body, settings=settings)
    if reply.answer_id and not reply.reused:
        schedule_index(request, background, settings, learner_id)
    return reply
