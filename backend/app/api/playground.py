import logging

from fastapi import APIRouter, BackgroundTasks, Request

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
    factory = getattr(request.app.state, "session_factory", None)
    if reply.answer_id and not reply.reused and factory is not None:

        async def index_saved() -> None:
            from app.orchestrator.answer_index import populate

            try:
                async with factory() as cache_db:
                    await populate(cache_db, settings, learner_id, limit=16)
            except Exception as exc:  # noqa: BLE001 — optional indexing cannot invalidate delivered answer
                logging.getLogger(__name__).warning(
                    "Answer indexing unavailable: %s", type(exc).__name__
                )

        background.add_task(index_saved)
    return reply
