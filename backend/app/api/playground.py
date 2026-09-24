from fastapi import APIRouter

from app.api.deps import DB, Gateway, Learner
from app.orchestrator import playground
from app.schemas.playground import PlaygroundReply, PlaygroundRequest

router = APIRouter(prefix="/playground", tags=["playground"])


@router.post(
    "/tutor",
    summary="Explain, hint or discuss a bounded coding workspace",
    response_model=PlaygroundReply,
)
async def tutor(
    body: PlaygroundRequest, db: DB, learner: Learner, gateway: Gateway
) -> PlaygroundReply:
    return await playground.respond(db, gateway, learner.id, body)
