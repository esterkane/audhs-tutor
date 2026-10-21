import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, Request
from fastapi.responses import StreamingResponse

from app.api.answer_jobs import schedule_index
from app.api.deps import DB, Gateway, Learner, Repo, SettingsDep
from app.api.sse import sse, with_heartbeats
from app.core.errors import AppError
from app.core.tutor_timing import mark as timing_mark
from app.db import workspace_requests
from app.kernel import session as ksession
from app.orchestrator.tutor import TutorTurn
from app.schemas.tutor import TurnDone, TurnMeta, TurnRequest

logger = logging.getLogger(__name__)
TUTOR_FAILED = (
    "The tutor response could not be completed. Some work may already be saved. "
    "Keep any received text and check saved answers before starting another request."
)

router = APIRouter(prefix="/tutor", tags=["tutor"])


def _intent_payload(body: TurnRequest) -> dict[str, Any]:
    # The default kind must retain pre-existing request identities for explicit recovery.
    exclude = {"assessment_answer_id"} if body.assessment_answer_id is None else set()
    if body.explanation_kind == "lesson":
        exclude.add("explanation_kind")
    return {"surface": "lesson_turn", **body.model_dump(mode="json", exclude=exclude)}


@router.post("/stream", summary="One tutor turn as SSE (meta, token*, done | error)")
async def stream(
    body: TurnRequest,
    db: DB,
    gateway: Gateway,
    repo: Repo,
    settings: SettingsDep,
    learner: Learner,
    request: Request,
    background: BackgroundTasks,
    idempotency_key: Annotated[UUID | None, Header()] = None,
) -> StreamingResponse:
    timing_mark("dependencies_ready")
    learner_id = learner.id
    identity = None
    saved = None
    if idempotency_key is not None:
        identity, saved = await workspace_requests.claim(
            db,
            learner_id,
            body.session_id,
            str(idempotency_key),
            _intent_payload(body),
        )
    turn = TutorTurn(
        db,
        gateway,
        repo,
        quarantine_below_trust=settings.quarantine_below_trust,
        settings=settings,
        recovery=request.app.state.answer_recovery,
    )

    async def gen() -> AsyncIterator[bytes]:
        try:
            if saved is not None:
                timing_mark("replay_started")
                restored = TurnDone.model_validate(saved["done"])
                if saved.get("meta") is not None:
                    yield sse(
                        "meta",
                        TurnMeta.model_validate(saved["meta"])
                        .model_copy(update={"replayed": True})
                        .model_dump(),
                    )
                # Existing clients assemble partial output from tokens; replay it without inference.
                if restored.text:
                    yield sse("token", {"text": restored.text})
                yield sse("done", restored.model_dump())
                return
            meta: dict[str, Any] | None = None
            await ksession.get_owned(db, body.session_id, learner.id)
            async for kind, data in turn.run(body):
                if kind == "meta":
                    meta = data
                if kind == "done" and identity is not None:
                    await workspace_requests.complete(
                        db, learner_id, identity, {"meta": meta, "done": data}
                    )
                if kind == "done" and data.get("answer_id"):
                    schedule_index(request, background, settings, learner_id)
                if kind == "done":
                    timing_mark("done_ready")
                yield sse(kind, data)
        except AppError as e:
            timing_mark("stream_error")
            yield sse("error", {"code": e.code, "message": e.message})
        except (KeyError, ValueError) as e:
            timing_mark("stream_error")
            yield sse("error", {"code": "bad_request", "message": str(e)})
        except Exception:  # never leave the stream hanging; detail goes to the log, not the learner
            logger.exception("tutor turn failed")
            timing_mark("stream_error")
            yield sse("error", {"code": "tutor_failed", "message": TUTOR_FAILED})

    return StreamingResponse(
        with_heartbeats(gen()),
        media_type="text/event-stream",
        background=background,
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/turn",
    summary="One tutor turn, buffered (tests, scripts, benchmarks)",
    response_model=TurnDone,
)
async def turn(
    body: TurnRequest,
    db: DB,
    gateway: Gateway,
    repo: Repo,
    settings: SettingsDep,
    learner: Learner,
    request: Request,
    background: BackgroundTasks,
    idempotency_key: Annotated[UUID | None, Header()] = None,
) -> TurnDone:
    await ksession.get_owned(db, body.session_id, learner.id)
    done = None
    learner_id = learner.id
    identity = None
    if idempotency_key is not None:
        identity, saved = await workspace_requests.claim(
            db,
            learner_id,
            body.session_id,
            str(idempotency_key),
            _intent_payload(body),
        )
        if saved is not None:
            return TurnDone.model_validate(saved["done"])
    meta: dict[str, Any] | None = None
    turn = TutorTurn(
        db,
        gateway,
        repo,
        quarantine_below_trust=settings.quarantine_below_trust,
        settings=settings,
        recovery=request.app.state.answer_recovery,
    )
    async for kind, data in turn.run(body):
        if kind == "meta":
            meta = data
        if kind == "done":
            done = data
    assert done is not None
    if identity is not None:
        await workspace_requests.complete(db, learner_id, identity, {"meta": meta, "done": done})
    if done.get("answer_id"):
        schedule_index(request, background, settings, learner_id)
    return TurnDone.model_validate(done)
