from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import DB, Gateway, Repo
from app.api.sse import sse
from app.orchestrator.tutor import TutorTurn
from app.schemas.tutor import TurnDone, TurnRequest

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/stream", summary="One tutor turn as SSE (meta, token*, done | error)")
async def stream(body: TurnRequest, db: DB, gateway: Gateway, repo: Repo) -> StreamingResponse:
    turn = TutorTurn(db, gateway, repo)

    async def gen() -> AsyncIterator[bytes]:
        try:
            async for kind, data in turn.run(body):
                yield sse(kind, data)
        except (KeyError, ValueError) as e:
            yield sse("error", {"code": "bad_request", "message": str(e)})
        except Exception as e:  # never leave the stream hanging
            yield sse("error", {"code": "tutor_failed", "message": f"{type(e).__name__}: {e}"})

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
async def turn(body: TurnRequest, db: DB, gateway: Gateway, repo: Repo) -> TurnDone:
    done = None
    async for kind, data in TutorTurn(db, gateway, repo).run(body):
        if kind == "done":
            done = data
    assert done is not None
    return TurnDone.model_validate(done)
