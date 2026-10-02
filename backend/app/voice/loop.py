"""The voice loop (P9): one WebSocket per conversation.

client → server: {"type":"start", session_id, skill_id?, lang?, text_only?, conversation?}
                 binary frames = PCM16 mono 16 kHz audio
                 {"type":"end_of_speech"} (client VAD) · {"type":"text", text} (typed fallback)
                 {"type":"interrupt"} (barge-in / stop playback) · {"type":"stop"}
server → client: {"type":"ready", stt, tts, vad, text_only} · {"type":"listening"} ·
                 {"type":"transcript", text, language} · {"type":"nothing_heard"} ·
                 {"type":"token", text} · {"type":"audio", pcm16_b64, sample_rate} ·
                 {"type":"done", turn, latency} · {"type":"interrupted"} · {"type":"error", message}

The tutor turn itself is the ordinary `TutorTurn.run` (bounded ContextPacket, citations, policy,
events); this module only adds ears and a mouth. Recordings are kept only when the learner opted in
(`voice.retain_audio`, under VOICE_DIR/<session>/, pruned by `voice.retention_days`); otherwise the
utterance lives in memory for the duration of the transcription. Every turn emits `spoke` with the
measured component latencies."""

from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import workspace_requests
from app.db.events import EventWriter, Verb
from app.db.traces import ModelCallRecord, write_model_call
from app.kernel import preferences
from app.kernel import session as ksession
from app.orchestrator.tutor import TutorTurn
from app.schemas.common import ActivityType, Domain, ObjectType
from app.schemas.tutor import TurnDone, TurnRequest
from app.schemas.voice import VoiceResultOut
from app.voice import recovery
from app.voice.stt import Stt
from app.voice.tts import Tts
from app.voice.vad import Vad, pcm16_seconds, wav_bytes

_request_identity: ContextVar[str | None] = ContextVar("voice_request_identity", default=None)

MAX_UTTERANCE_S = 60.0
MIN_SPEECH_MS = 300
MAX_FRAME_BYTES = 32_000  # one second of PCM16 16 kHz per message
_RETAINED_NAME = re.compile(r"\d{8}T\d{12}\.wav")
MARKER = ".audhs-voice"
_SENTENCE = re.compile(r"(?<=[.!?…])\s+")
_CITATION = re.compile(r"\s*\[\d+(?:,\s*\d+)*\]")
_MARKUP = re.compile(r"[*_`#>]+")


def speakable(text: str) -> str:
    """What the voice says: no citation brackets, no markdown markers, no leading '(analogy)' tag."""
    text = _CITATION.sub("", text)
    text = _MARKUP.sub("", text)
    text = re.sub(r"^\s*\((?:[a-z_ ]+)\)\s*", "", text)
    return " ".join(text.split())


@dataclass
class TurnTiming:
    t_start: float
    stt_ms: int = 0
    llm_first_token_ms: int | None = None
    tts_first_audio_ms: int | None = None
    total_ms: int = 0
    interrupted: bool = False
    first_chunk: str | None = None  # "clause" | "sentence": what the first TTS request carried

    def dict(self) -> dict[str, Any]:
        return {
            "stt_ms": self.stt_ms,
            "llm_first_token_ms": self.llm_first_token_ms,
            "tts_first_audio_ms": self.tts_first_audio_ms,
            "total_ms": self.total_ms,
            "interrupted": self.interrupted,
        }


@dataclass
class VoiceState:
    session_id: str
    skill_id: str | None
    lang: str | None
    text_only: bool
    conversation: bool
    voice: str
    early_speech: bool = True
    buffer: bytearray = field(default_factory=bytearray)
    speaking: bool = False
    identified_capture: bool = False
    capture_id: str | None = None
    active_request_id: str | None = None


def sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE.split(text.strip()) if s]


_CLAUSE = re.compile(r"(?<=[,;:])\s+")
_SENTENCE_END = re.compile(r"[.!?…]\s*$")
MIN_CLAUSE_WORDS = 3


def first_clause(text: str) -> tuple[str, str] | None:
    """`(clause, rest)` at the first comma/semicolon/colon that closes at least three *spoken*
    words and is followed by more text — the earliest point where speaking can start without a
    fragment. Delimiters inside code spans or open brackets do not count; a short interjection
    ("Yes, …") is skipped and the next delimiter is tried."""
    for m in _CLAUSE.finditer(text):
        head, rest = text[: m.start()], text[m.end() :]
        if head.count("`") % 2 or head.count("(") != head.count(")"):
            continue
        if len(speakable(head).split()) < MIN_CLAUSE_WORDS:
            continue
        if not rest.strip():
            return None  # the clause is closed but nothing follows yet: wait for more tokens
        return head.strip(), rest
    return None


def speech_chunks(pending: str, *, first: bool, early: bool) -> tuple[list[str], str]:
    """What to hand to the speaker now and what to keep. Whole sentences always; for the very
    first utterance of a turn (`first`) with `early` on, the first clause of the first sentence
    goes out as soon as it is closed, so first audio does not wait for the sentence to finish
    (measured gain: docs/slices/voice-loop.md)."""
    ends = list(_SENTENCE.finditer(pending))
    if ends:
        # keep the remainder verbatim: `sentences()` would strip the whitespace a streaming
        # provider puts *after* a token and glue the next word onto it ("Thenone")
        cut = ends[-1].end()
        return sentences(pending[:cut]), pending[cut:]
    if first and early:
        fc = first_clause(pending)
        if fc is not None:
            return [fc[0]], fc[1]
    return [], pending


class VoiceLoop:
    def __init__(
        self,
        db: AsyncSession,
        turn: TutorTurn,
        *,
        stt: Stt | None,
        tts: Tts | None,
        vad: Vad,
        voice_dir: Path,
        learner_id: str,
    ) -> None:
        self.db = db
        self.turn = turn
        self.stt = stt
        self.tts = tts
        self.vad = vad
        self.voice_dir = voice_dir
        self.learner_id = learner_id
        self._speak_task: asyncio.Task[None] | None = None
        self._turn_task: asyncio.Task[None] | None = None
        self._interrupted = asyncio.Event()
        self._busy_beyond_interrupt = False

    # ------------------------------------------------------------------ protocol
    async def serve(self, ws: WebSocket) -> None:
        state: VoiceState | None = None
        try:
            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                if msg.get("bytes") is not None:
                    if state is None:
                        continue
                    if state.identified_capture and state.capture_id is None:
                        continue  # frames queued after a finished capture cannot start another turn
                    token = _request_identity.set(state.capture_id)
                    try:
                        await self._on_audio(ws, state, msg["bytes"])
                    finally:
                        _request_identity.reset(token)
                    continue
                try:
                    data = json.loads(msg.get("text") or "{}")
                except json.JSONDecodeError:
                    await self._send(ws, {"type": "error", "message": "not JSON", "protocol": True})
                    continue
                kind = data.get("type")
                if kind == "start":
                    if state is not None:
                        if not await self._wait_previous(ws):
                            continue
                    state = await self._start(ws, data)
                elif state is None:
                    await self._send(
                        ws, {"type": "error", "message": "send start first", "protocol": True}
                    )
                elif kind == "capture" and state.identified_capture:
                    try:
                        identity = str(UUID(str(data.get("request_id"))))
                    except ValueError:
                        await self._send(
                            ws,
                            {
                                "type": "error",
                                "message": "Invalid capture identity.",
                                "protocol": True,
                            },
                        )
                        continue
                    token = _request_identity.set(identity)
                    try:
                        if not await self._wait_previous(ws):
                            continue
                        state.buffer.clear()
                        self.vad.reset()
                        state.capture_id = identity
                        state.active_request_id = identity
                    finally:
                        _request_identity.reset(token)
                elif kind == "end_of_speech":
                    if state.identified_capture and (
                        state.capture_id is None or data.get("request_id") != state.capture_id
                    ):
                        continue
                    token = _request_identity.set(state.capture_id)
                    try:
                        await self._finish_utterance(ws, state)
                    finally:
                        _request_identity.reset(token)
                elif kind == "text":
                    text = str(data.get("text") or "").strip()
                    identity = data.get("request_id")
                    if identity is not None:
                        try:
                            identity = str(UUID(str(identity)))
                        except ValueError:
                            await self._send(
                                ws,
                                {
                                    "type": "error",
                                    "message": "Invalid voice request identity.",
                                    "protocol": True,
                                },
                            )
                            continue
                    if text:
                        token = _request_identity.set(identity)
                        try:
                            if not await self._wait_previous(ws):
                                continue
                            if state.identified_capture:
                                state.capture_id = None
                                state.buffer.clear()
                                self.vad.reset()
                            state.active_request_id = identity
                            # Child response and speaker tasks inherit this immutable context.
                            self._interrupted.clear()
                            self._turn_task = asyncio.create_task(
                                self._respond(ws, state, text, stt_ms=0)
                            )
                        finally:
                            _request_identity.reset(token)
                elif kind == "interrupt":
                    identity = data.get("request_id")
                    if (
                        identity is not None or state.identified_capture
                    ) and identity != state.active_request_id:
                        continue  # delayed controls cannot interrupt a newer request
                    token = _request_identity.set(state.active_request_id)
                    try:
                        # Playback stops locally; acknowledgement is not terminal cleanup.
                        self._interrupted.set()
                        await self._send(ws, {"type": "interrupted"})
                        await self._interrupt()
                    finally:
                        _request_identity.reset(token)
                elif kind == "stop":
                    await self._interrupt()
                    break
        except WebSocketDisconnect:
            pass
        finally:
            await self._interrupt()

    async def _wait_previous(self, ws: WebSocket) -> bool:
        """Do not reuse the shared DB session while cooperative interruption is unfinished."""
        await self._interrupt()
        if not self._busy_beyond_interrupt:
            return True
        await self._send(
            ws,
            {
                "type": "error",
                "message": (
                    "The previous voice response is still finishing. "
                    "This new request was not started or queued. Wait, then send it again."
                ),
                "fallback": "text",
            },
        )
        return False

    async def _send(self, ws: WebSocket, payload: dict[str, Any]) -> None:
        identity = _request_identity.get()
        if identity is not None:
            payload = {**payload, "request_id": identity}
        try:
            await ws.send_text(json.dumps(payload, ensure_ascii=False))
        except (WebSocketDisconnect, RuntimeError):
            pass

    async def _start(self, ws: WebSocket, data: dict[str, Any]) -> VoiceState:
        session = await ksession.get(self.db, str(data.get("session_id") or ""))
        if session.learner_id != self.learner_id:
            raise KeyError("session not found")
        voice = str(await preferences.get(self.db, self.learner_id, "voice.voice") or "")
        if not voice and self.tts is not None:
            try:
                voice = (await self.tts.voices() or [""])[0]
            except Exception:
                voice = ""
        retain = bool(await preferences.get(self.db, self.learner_id, "voice.retain_audio"))
        early = bool(await preferences.get(self.db, self.learner_id, "voice.early_speech"))
        days = int(await preferences.get(self.db, self.learner_id, "voice.retention_days") or 7)
        await asyncio.to_thread(prune, self.voice_dir, days if retain else 0)
        text_only = bool(data.get("text_only")) or self.stt is None or self.tts is None
        state = VoiceState(
            session_id=session.id,
            skill_id=data.get("skill_id"),
            lang=data.get("lang"),
            text_only=text_only,
            conversation=bool(data.get("conversation")),
            voice=voice,
            early_speech=early,
            identified_capture=data.get("request_identity") == "utterance-v1",
        )
        await self._send(
            ws,
            {
                "type": "ready",
                "control_identity": True,
                "request_identity": "utterance-v1" if state.identified_capture else "typed-v1",
                "stt": self.stt.registry_id if self.stt else None,
                "tts": self.tts.model if self.tts else None,
                "vad": self.vad.name,
                "text_only": text_only,
                "why_text_only": None
                if not text_only
                else ("requested" if data.get("text_only") else "speech components not ready"),
            },
        )
        self.vad.reset()
        return state

    # ------------------------------------------------------------------ audio in
    async def _on_audio(self, ws: WebSocket, state: VoiceState, frame: bytes) -> None:
        if state.text_only or self.stt is None:
            return
        if len(frame) > MAX_FRAME_BYTES:
            await self._send(
                ws, {"type": "error", "message": "audio frames must be ≤ 1 s", "protocol": True}
            )
            return
        if self._busy_beyond_interrupt:
            # the previous answer is still finishing (a model that has not produced a token yet
            # cannot see the flag); do not start a second turn on the same session
            return
        status = self.vad.feed(frame)
        if status == "silence" and not state.buffer:
            return  # leading / trailing silence: nothing to do, never a barge-in
        if status == "speech" and self.speaking_now():
            # barge-in: the learner talks while the tutor speaks → stop playback first
            if not await self._wait_previous(ws):
                return
            await self._send(ws, {"type": "interrupted"})
        if not state.buffer:
            await self._send(ws, {"type": "listening"})
        state.buffer += frame
        if len(state.buffer) / 32_000 > MAX_UTTERANCE_S or status == "end":
            await self._finish_utterance(ws, state)

    def speaking_now(self) -> bool:
        return (self._speak_task is not None and not self._speak_task.done()) or (
            self._turn_task is not None and not self._turn_task.done()
        )

    async def _finish_utterance(self, ws: WebSocket, state: VoiceState) -> None:
        if state.identified_capture:
            state.capture_id = None
            await self._send(ws, {"type": "processing"})
        pcm = bytes(state.buffer)
        state.buffer = bytearray()
        heard_ms = getattr(self.vad, "heard_ms", 0)
        self.vad.reset()
        if self.stt is None or not pcm or heard_ms < MIN_SPEECH_MS:
            await self._send(ws, {"type": "nothing_heard"})
            return
        # a new utterance ends the running answer first: the shared DB session is used by one
        # coroutine at a time (SQLAlchemy async sessions are not safe for concurrent use)
        if not await self._wait_previous(ws):
            return
        t0 = time.perf_counter()
        try:
            res = await self.stt.transcribe(pcm, language=state.lang)
        except Exception as e:
            await write_model_call(
                self.db,
                ModelCallRecord(
                    provider="mlx",
                    model=self.stt.registry_id,
                    registry_id=self.stt.registry_id,
                    task="stt",
                    ok=False,
                    error=str(e)[:300],
                    outcome="error",
                    usage_source="unavailable",
                    cost_status="free",
                    learner_id=self.learner_id,
                    session_id=state.session_id,
                ),
            )
            await self._send(
                ws,
                {
                    "type": "error",
                    "message": "The speech recogniser did not answer. Type your question instead.",
                    "fallback": "text",
                },
            )
            return
        stt_ms = int((time.perf_counter() - t0) * 1000)
        await write_model_call(
            self.db,
            ModelCallRecord(
                provider="mlx",
                model=res.model,
                registry_id=res.registry_id,
                task="stt",
                latency_ms=res.latency_ms,
                usage_source="unavailable",
                cost_status="free",
                learner_id=self.learner_id,
                session_id=state.session_id,
                metadata={"seconds": pcm16_seconds(pcm)},
            ),
        )
        await self._retain(state, pcm)
        if not res.text.strip():
            await self._send(ws, {"type": "nothing_heard"})
            return
        await self._send(ws, {"type": "transcript", "text": res.text, "language": res.language})
        self._interrupted.clear()
        self._turn_task = asyncio.create_task(self._respond(ws, state, res.text, stt_ms=stt_ms))

    async def _retain(self, state: VoiceState, pcm: bytes) -> None:
        """Opt-in only. Files land under VOICE_DIR/<session>/<utc>.wav and older files beyond the
        retention window are pruned on every write. Without the opt-in nothing touches disk."""
        if not await preferences.get(self.db, self.learner_id, "voice.retain_audio"):
            return
        days = int(await preferences.get(self.db, self.learner_id, "voice.retention_days") or 7)
        folder = self.voice_dir / state.session_id
        await asyncio.to_thread(folder.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread((self.voice_dir / MARKER).touch)  # marks the folder as ours
        name = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + ".wav"
        await asyncio.to_thread((folder / name).write_bytes, wav_bytes(pcm))
        await asyncio.to_thread(prune, self.voice_dir, days)

    # ------------------------------------------------------------------ respond
    async def _respond(self, ws: WebSocket, state: VoiceState, text: str, *, stt_ms: int) -> None:
        try:
            req = TurnRequest(
                session_id=state.session_id,
                text=text,
                skill_id=state.skill_id,
                conversation_lang=state.lang if state.conversation else None,
                spoken=not state.text_only,
            )
        except ValueError:
            await self._send(
                ws,
                {
                    "type": "error",
                    "message": "The voice request is invalid. Shorten the text before sending again.",
                    "fallback": "text",
                },
            )
            return
        request_id = _request_identity.get()
        claim_id = None
        if request_id is not None:
            try:
                claim_id, saved = await workspace_requests.claim(
                    self.db,
                    self.learner_id,
                    state.session_id,
                    recovery.key(request_id),
                    {
                        "surface": "voice_turn",
                        "session_id": state.session_id,
                        "skill_id": state.skill_id,
                        "text": text,
                        "language": state.lang,
                        "conversation": state.conversation,
                        "text_only": state.text_only,
                    },
                )
            except AppError as error:
                await self._send(
                    ws, {"type": "error", "message": error.message, "fallback": "text"}
                )
                return
            except Exception:
                await self.db.rollback()
                await self._send(
                    ws,
                    {
                        "type": "error",
                        "message": "Voice request recovery could not be prepared. Keep your text and try again later.",
                        "fallback": "text",
                    },
                )
                return
            if saved is not None:
                result = VoiceResultOut.model_validate(saved)
                await self._send(ws, {"type": "token", "text": result.text or ""})
                await self._send(
                    ws,
                    {
                        "type": "done",
                        "turn": result.turn.model_dump(mode="json") if result.turn else None,
                        "replayed": True,
                        "recovery_status": result.status,
                        "latency": {"interrupted": result.interrupted},
                    },
                )
                return
        if self._interrupted.is_set():
            result = VoiceResultOut(
                request_id=request_id or "",
                status="partial",
                transcript=text,
                text="",
                interrupted=True,
            )
            if await self._persist_result(ws, claim_id, result):
                await self._send(
                    ws,
                    {
                        "type": "done",
                        "turn": None,
                        "recovery_status": "partial",
                        "latency": {"interrupted": True},
                    },
                )
            return
        await self._run_response(
            ws, state, text, req=req, stt_ms=stt_ms, claim_id=claim_id, request_id=request_id
        )

    async def _persist_result(
        self, ws: WebSocket, claim_id: str | None, result: VoiceResultOut
    ) -> bool:
        if claim_id is None:
            return True
        try:
            await workspace_requests.complete(
                self.db, self.learner_id, claim_id, result.model_dump(mode="json")
            )
            return True
        except Exception:
            await self.db.rollback()
            await self._send(
                ws,
                {
                    "type": "error",
                    "message": (
                        "Voice recovery could not be saved. Keep received text; "
                        "the request will not run again automatically."
                    ),
                },
            )
            return False

    async def _run_response(
        self,
        ws: WebSocket,
        state: VoiceState,
        text: str,
        *,
        stt_ms: int,
        req: TurnRequest,
        claim_id: str | None,
        request_id: str | None,
    ) -> None:
        timing = TurnTiming(t_start=time.perf_counter(), stt_ms=stt_ms)
        pending = ""
        received = ""
        done_payload: dict[str, Any] | None = None
        first_token = True
        nothing_spoken_yet = True
        speak_queue: asyncio.Queue[str | None] = asyncio.Queue()
        speaker: asyncio.Task[None] | None = None
        tts_log: list[ModelCallRecord] = []
        if not state.text_only and self.tts is not None:
            speaker = asyncio.create_task(self._speaker(ws, state, speak_queue, timing, tts_log))
            self._speak_task = speaker
        agen = self.turn.run(req)
        try:
            async for kind, data in agen:
                if self._interrupted.is_set():
                    break
                if kind == "token":
                    if first_token:
                        timing.llm_first_token_ms = int(
                            (time.perf_counter() - timing.t_start) * 1000
                        )
                        first_token = False
                    tok = str(data.get("text", ""))
                    await self._send(ws, {"type": "token", "text": tok})
                    received += tok
                    pending += tok
                    ready, pending = speech_chunks(
                        pending, first=nothing_spoken_yet, early=state.early_speech
                    )
                    for s in ready:
                        spoken_text = speakable(s)
                        if spoken_text:
                            if nothing_spoken_yet:
                                timing.first_chunk = (
                                    "sentence" if _SENTENCE_END.search(s) else "clause"
                                )
                            await speak_queue.put(spoken_text)
                            nothing_spoken_yet = False
                elif kind == "done":
                    done_payload = data
                elif kind == "meta":
                    await self._send(ws, {"type": "meta", **data})
            if speakable(pending) and not self._interrupted.is_set():
                await speak_queue.put(speakable(pending))
        except Exception as e:
            await self._send(
                ws,
                {
                    "type": "error",
                    "message": (
                        "The voice response could not finish. Some work may already be saved; "
                        "keep received text and check saved answers."
                    ),
                    "detail": type(e).__name__,
                },
            )
        finally:
            aclose = getattr(agen, "aclose", None)
            if aclose is not None:
                try:
                    await aclose()  # runs the tutor's own finally: trace, `explained`, checkpoint
                except Exception:
                    pass
            await speak_queue.put(None)
            if speaker is not None:
                try:
                    await speaker
                except asyncio.CancelledError:
                    pass
            timing.total_ms = int((time.perf_counter() - timing.t_start) * 1000)
            timing.interrupted = self._interrupted.is_set()
            for rec in tts_log:  # written here, after the turn released the session
                await write_model_call(self.db, rec)
            await self._emit_spoke(state, timing)
            deliver_terminal = True
            if claim_id is not None and request_id is not None:
                complete = done_payload is not None and done_payload.get("outcome") != "partial"
                result = VoiceResultOut(
                    request_id=request_id,
                    status="completed" if complete else "partial",
                    transcript=text,
                    text=str(done_payload.get("text", received))
                    if complete and done_payload
                    else received,
                    turn=TurnDone.model_validate(done_payload) if done_payload else None,
                    interrupted=timing.interrupted,
                )
                deliver_terminal = await self._persist_result(ws, claim_id, result)
            if deliver_terminal:
                await self._send(
                    ws,
                    {"type": "done", "turn": done_payload, "latency": timing.dict()},
                )

    async def _speaker(
        self,
        ws: WebSocket,
        state: VoiceState,
        queue: asyncio.Queue[str | None],
        timing: TurnTiming,
        tts_log: list[ModelCallRecord],
    ) -> None:
        assert self.tts is not None
        while True:
            try:
                text = await asyncio.wait_for(queue.get(), timeout=0.25)
            except TimeoutError:
                if self._interrupted.is_set():
                    return
                continue
            if text is None or self._interrupted.is_set():
                return
            t0 = time.perf_counter()
            try:
                async for chunk in self.tts.stream(text, voice=state.voice, lang=state.lang):
                    if self._interrupted.is_set():
                        return
                    if timing.tts_first_audio_ms is None:
                        timing.tts_first_audio_ms = int(
                            (time.perf_counter() - timing.t_start) * 1000
                        )
                    await self._send(
                        ws,
                        {
                            "type": "audio",
                            "pcm16_b64": base64.b64encode(chunk.pcm16).decode(),
                            "sample_rate": chunk.sample_rate,
                        },
                    )
                tts_log.append(
                    ModelCallRecord(
                        provider="kokoro",
                        model=self.tts.model,
                        registry_id=self.tts.registry_id,
                        task="tts",
                        latency_ms=int((time.perf_counter() - t0) * 1000),
                        tokens_in=len(text.split()),
                        usage_source="estimated",
                        cost_status="free",
                        learner_id=self.learner_id,
                        session_id=state.session_id,
                    )
                )
            except Exception as e:
                tts_log.append(
                    ModelCallRecord(
                        provider="kokoro",
                        model=self.tts.model,
                        registry_id=self.tts.registry_id,
                        task="tts",
                        ok=False,
                        error=str(e)[:300],
                        outcome="error",
                        usage_source="unavailable",
                        cost_status="free",
                        learner_id=self.learner_id,
                        session_id=state.session_id,
                    )
                )
                await self._send(
                    ws,
                    {
                        "type": "error",
                        "message": "The voice did not play. The answer stays readable as text.",
                        "fallback": "text",
                    },
                )
                return

    async def _interrupt(self) -> None:
        """Cooperative: set the flag and wait for the turn/speaker to notice and finish their own
        clean-up (trace, events, model_call rows). Tasks are never cancelled outright — a cancel
        inside an aiosqlite call leaves the shared connection wedged."""
        self._interrupted.set()
        for t in (self._speak_task, self._turn_task):
            if t is not None and not t.done() and t is not asyncio.current_task():
                try:
                    await asyncio.wait_for(asyncio.shield(t), timeout=15)
                except TimeoutError:
                    # still running (e.g. a cold model load): keep the reference so nothing else
                    # touches the session; the client is told to wait or type
                    self._busy_beyond_interrupt = True
                    return
                except Exception:
                    pass
        self._busy_beyond_interrupt = False
        self._speak_task = None
        self._turn_task = None

    async def shutdown(self) -> None:
        """Keep session ownership until every child finishes, even if the socket owner is cancelled.

        The interactive interrupt timeout is not permission to close a session still in use.
        Provider timeouts normally bound this drain; a wedged in-process provider cannot be
        safely killed while it owns database cleanup. Never cancel a child inside SQLite work.
        """
        self._interrupted.set()
        cancelled = False
        # The turn may create its speaker after shutdown starts (e.g. after a ledger claim).
        # Await the turn first, then read the final speaker reference.
        for name in ("_turn_task", "_speak_task"):
            task = getattr(self, name)
            if task is None or task is asyncio.current_task():
                continue
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    cancelled = True
                except Exception:
                    break
            if not task.cancelled():
                task.exception()  # observe failures even when the task finished before shutdown
            setattr(self, name, None)
        self._busy_beyond_interrupt = False
        if cancelled:
            raise asyncio.CancelledError

    async def _emit_spoke(self, state: VoiceState, timing: TurnTiming) -> None:
        session = await ksession.get(self.db, state.session_id)
        events = EventWriter(
            self.db,
            ksession.event_context(
                session,
                domain=Domain.LANGUAGE if state.conversation else Domain.AI_ML,
                activity=ActivityType.CHAT,
            ),
        )
        await events.emit(
            Verb.SPOKE,
            ObjectType.TURN,
            state.session_id,
            result={
                "stt_ms": timing.stt_ms,
                "llm_first_token_ms": timing.llm_first_token_ms or 0,
                "tts_first_audio_ms": timing.tts_first_audio_ms or 0,
                "total_ms": timing.total_ms,
                "interrupted": timing.interrupted,
            },
            context={
                "first_chunk": timing.first_chunk,
                "stt_model": self.stt.registry_id if self.stt else None,
                "tts_model": self.tts.model if self.tts else None,
                "lang": state.lang,
            },
        )


def prune(voice_dir: Path, days: int) -> int:
    """Delete retained recordings older than `days` (0 = all); returns how many were removed.
    Touches only files the loop wrote itself: `<voice_dir>/<session>/<utc>.wav` under a folder
    carrying the marker file — a misconfigured VOICE_DIR can never delete other recordings."""
    if not voice_dir.is_dir() or not (voice_dir / MARKER).is_file():
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=days)
    removed = 0
    for folder in voice_dir.iterdir():
        if not folder.is_dir():
            continue
        for wav in folder.iterdir():
            if not wav.is_file() or not _RETAINED_NAME.fullmatch(wav.name):
                continue
            try:
                if days == 0 or datetime.fromtimestamp(wav.stat().st_mtime, UTC) < cutoff:
                    wav.unlink()
                    removed += 1
            except OSError:
                continue
        try:
            folder.rmdir()  # empty session folders go
        except OSError:
            pass
    return removed


Factory = Callable[[AsyncSession], Awaitable[tuple[Stt | None, Tts | None, Vad]]]
__all__ = [
    "VoiceLoop",
    "prune",
    "sentences",
    "speakable",
    "first_clause",
    "speech_chunks",
    "TurnTiming",
    "Factory",
    "AsyncIterator",
]
