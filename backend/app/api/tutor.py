import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import DB, Gateway, Repo, SettingsDep
from app.api.sse import sse
from app.orchestrator.tutor import TutorTurn
from app.schemas.tutor import TurnDone, TurnRequest

logger = logging.getLogger(__name__)
TUTOR_FAILED = (
    "The tutor model did not answer. Nothing was changed. Try again, or check Models › Routing."
)

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/stream", summary="One tutor turn as SSE (meta, token*, done | error)")
async def stream(
    body: TurnRequest, db: DB, gateway: Gateway, repo: Repo, settings: SettingsDep
) -> StreamingResponse:
    turn = TutorTurn(db, gateway, repo, quarantine_below_trust=settings.quarantine_below_trust)

    async def gen() -> AsyncIterator[bytes]:
        try:
            async for kind, data in turn.run(body):
                yield sse(kind, data)
        except (KeyError, ValueError) as e:
            yield sse("error", {"code": "bad_request", "message": str(e)})
        except Exception:  # never leave the stream hanging; detail goes to the log, not the learner
            logger.exception("tutor turn failed")
            yield sse("error", {"code": "tutor_failed", "message": TUTOR_FAILED})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/turn",
    summary="One tutor turn, buffered (tests, scripts, benchmarks)",
    response_model=TurnDone,
)
async def turn(
    body: TurnRequest, db: DB, gateway: Gateway, repo: Repo, settings: SettingsDep
) -> TurnDone:
    done = None
    turn = TutorTurn(db, gateway, repo, quarantine_below_trust=settings.quarantine_below_trust)
    async for kind, data in turn.run(body):
        if kind == "done":
            done = data
    assert done is not None
    return TurnDone.model_validate(done)
