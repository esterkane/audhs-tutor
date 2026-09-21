"""P9 voice: readiness → install (registry pull jobs, Models screen) → verify → test → activate, and
the WebSocket loop. Nothing here downloads, starts a server or switches routes by itself."""

import base64
import logging
from typing import Any

from fastapi import APIRouter, Request, WebSocket
from pydantic import BaseModel

from app.api.deps import DB, Learner, SettingsDep, get_budget
from app.core.errors import AppError
from app.db.session import get_db
from app.kernel.learner import get_or_create_owner
from app.knowledge.repository import RetrievalRepository
from app.models_ai.gateway import ModelGateway
from app.models_ai.routing import Router
from app.orchestrator.tutor import TutorTurn
from app.voice import setup
from app.voice.loop import VoiceLoop

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])


class ComponentOut(BaseModel):
    ready: bool
    status: str
    detail: str
    action: str | None = None


class ReadinessOut(BaseModel):
    stt: ComponentOut
    tts: ComponentOut
    vad: ComponentOut
    tools: ComponentOut
    activated: bool
    retain_audio: bool
    retention_days: int
    voice: str
    can_activate: bool
    stt_id: str
    tts_id: str
    vad_id: str | None
    conversation_lang: str
    conversation_lang_supported: bool
    notes: list[str]


class ActivateIn(BaseModel):
    enabled: bool


class VerifyOut(BaseModel):
    stt: dict[str, Any] | None
    tts: dict[str, Any] | None
    problems: list[str]


class MicTestOut(BaseModel):
    text: str
    language: str | None
    latency_ms: int
    seconds: float
    recording_kept: bool = False


@router.get(
    "/readiness",
    summary="Is voice usable? Each component with the one step that fixes it",
    response_model=ReadinessOut,
)
async def readiness(db: DB, learner: Learner, settings: SettingsDep) -> ReadinessOut:
    return ReadinessOut(**(await setup.readiness(db, settings, learner.id)).dict())


@router.post(
    "/verify",
    summary="Load the installed speech components once and run a fixed sentence (no microphone)",
    response_model=VerifyOut,
)
async def verify(request: Request, db: DB, learner: Learner, settings: SettingsDep) -> VerifyOut:
    overrides = getattr(request.app.state, "voice_overrides", None)
    stt, tts, _ = await setup.adapters(db, settings, overrides)
    problems: list[str] = []
    out_stt: dict[str, Any] | None = None
    out_tts: dict[str, Any] | None = None
    if stt is None:
        problems.append("speech recognition is not installed (see readiness)")
    else:
        try:
            from app.voice.vad import silence

            out_stt = await setup.verify_stt(
                db, stt, silence(1.0), learner_id=learner.id, language=None
            )
        except Exception as e:
            problems.append(f"speech recognition loaded but failed: {type(e).__name__}")
    if tts is None:
        problems.append("the Kokoro voice server is not reachable (see readiness)")
    else:
        try:
            voice = (await setup.readiness(db, settings, learner.id)).voice
            res = await setup.verify_tts(db, tts, learner_id=learner.id, voice=voice, lang=None)
            out_tts = {
                "pcm16_b64": base64.b64encode(res["pcm16"]).decode(),
                "sample_rate": res["sample_rate"],
                "first_audio_ms": res["first_audio_ms"],
                "seconds": round(float(res["seconds"]), 2),
            }
        except Exception as e:
            problems.append(f"the voice server answered but synthesis failed: {type(e).__name__}")
    return VerifyOut(stt=out_stt, tts=out_tts, problems=problems)


@router.post(
    "/test-mic",
    summary="Transcribe one short test recording (raw body: mono 16 kHz WAV, ≤ 20 s); discarded",
    response_model=MicTestOut,
)
async def test_mic(request: Request, db: DB, learner: Learner, settings: SettingsDep) -> MicTestOut:
    # raw WAV body (no multipart dependency); bounded *before* it is buffered
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > setup.MAX_TEST_BYTES:
        raise AppError("too_large", "recording too large: at most 20 seconds", http_status=413)
    chunks: list[bytes] = []
    total = 0
    async for part in request.stream():
        total += len(part)
        if total > setup.MAX_TEST_BYTES:
            raise AppError("too_large", "recording too large: at most 20 seconds", http_status=413)
        chunks.append(part)
    data = b"".join(chunks)
    try:
        pcm = setup.parse_test_wav(data)
    except ValueError as e:
        raise AppError("bad_request", str(e), http_status=400) from e
    stt, _, _ = await setup.adapters(
        db, settings, getattr(request.app.state, "voice_overrides", None)
    )
    if stt is None:
        raise AppError("not_ready", "speech recognition is not installed yet (see readiness)", 409)
    try:
        res = await setup.verify_stt(db, stt, pcm, learner_id=learner.id, language=None)
    except Exception as e:
        raise AppError(
            "stt_failed", "the recogniser could not process the recording; set it up again", 502
        ) from e
    return MicTestOut(
        text=str(res["text"]),
        language=res["language"],
        latency_ms=int(res["latency_ms"]),
        seconds=len(pcm) / 32_000,
        recording_kept=False,
    )


@router.post(
    "/activate",
    summary="Turn voice on/off for sessions (explicit; needs STT and TTS ready)",
    response_model=ReadinessOut,
)
async def activate(
    body: ActivateIn, db: DB, learner: Learner, settings: SettingsDep
) -> ReadinessOut:
    ready = await setup.readiness(db, settings, learner.id)
    try:
        await setup.set_activation(db, learner.id, enabled=body.enabled, ready=ready)
    except ValueError as e:
        raise AppError("not_ready", str(e), http_status=409) from e
    return ReadinessOut(**(await setup.readiness(db, settings, learner.id)).dict())


def _own_origin(origin: str, host: str) -> bool:
    """Same host (any scheme/port on localhost) or the Vite dev origin."""
    from urllib.parse import urlsplit

    o = urlsplit(origin)
    if o.hostname in ("localhost", "127.0.0.1") and host.split(":")[0] in (
        "localhost",
        "127.0.0.1",
        "testserver",
    ):
        return True
    return o.netloc == host


@router.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    """The voice loop. Dependencies are built by hand: the WebSocket has no request-scoped `Depends`
    chain for the DB session in this app."""
    app = websocket.app
    settings = app.state.settings
    # CORS does not cover WebSockets: only our own origins may drive the tutor
    origin = websocket.headers.get("origin")
    if origin and not _own_origin(origin, websocket.headers.get("host", "")):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    async for db in get_db(websocket):  # type: ignore[arg-type]
        learner = await get_or_create_owner(db)
        overrides = getattr(app.state, "voice_overrides", None)
        stt, tts, vad = await setup.adapters(db, settings, overrides)
        gateway = ModelGateway(
            db,
            Router(settings.routing_profile),
            app.state.providers,
            get_budget(websocket, settings),  # type: ignore[arg-type]
        )
        repo: RetrievalRepository | None = getattr(app.state, "repo", None)
        if repo is None:
            # built inside the app's own loop/thread (tests hand over a factory; SQLite handles are
            # thread-bound), otherwise the production Qdrant repository
            factory = getattr(app.state, "repo_factory", None)
            if factory is not None:
                repo = factory()
            else:
                from app.knowledge.reindex import build_repo

                repo = await build_repo(db, settings)
            app.state.repo = repo
        turn = TutorTurn(db, gateway, repo, quarantine_below_trust=settings.quarantine_below_trust)
        loop = VoiceLoop(
            db,
            turn,
            stt=stt,
            tts=tts,
            vad=vad,
            voice_dir=settings.voice_dir_resolved,
            learner_id=learner.id,
        )
        try:
            await loop.serve(websocket)
        except KeyError as e:
            await websocket.send_json({"type": "error", "message": str(e).strip("'")})
        except Exception:  # never close 1011 silently: the client shows a literal message
            logger.exception("voice loop failed")
            try:
                await websocket.send_json(
                    {"type": "error", "message": "Voice stopped unexpectedly. Typing still works."}
                )
            except Exception:
                pass
        finally:
            try:
                await websocket.close()
            except RuntimeError:
                pass
        break
