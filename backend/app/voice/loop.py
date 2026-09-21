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
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventWriter, Verb
from app.db.traces import ModelCallRecord, write_model_call
from app.kernel import preferences
from app.kernel import session as ksession
from app.orchestrator.tutor import TutorTurn
from app.schemas.common import ActivityType, Domain, ObjectType
from app.schemas.tutor import TurnRequest
from app.voice.stt import Stt
from app.voice.tts import Tts
from app.voice.vad import Vad, pcm16_seconds, wav_bytes

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
    buffer: bytearray = field(default_factory=bytearray)
    speaking: bool = False


def sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE.split(text.strip()) if s]


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
                    await self._on_audio(ws, state, msg["bytes"])
                    continue
                try:
                    data = json.loads(msg.get("text") or "{}")
                except json.JSONDecodeError:
                    await self._send(ws, {"type": "error", "message": "not JSON", "protocol": True})
                    continue
                kind = data.get("type")
                if kind == "start":
                    if state is not None:
                        await self._interrupt()  # a restart ends the running turn first
                    state = await self._start(ws, data)
                elif state is None:
                    await self._send(
                        ws, {"type": "error", "message": "send start first", "protocol": True}
                    )
                elif kind == "end_of_speech":
                    await self._finish_utterance(ws, state)
                elif kind == "text":
                    text = str(data.get("text") or "").strip()
                    if text:
                        await self._interrupt()
                        self._turn_task = asyncio.create_task(
                            self._respond(ws, state, text, stt_ms=0)
                        )
                elif kind == "interrupt":
                    # acknowledge at once (playback stops client-side), then let the turn wind down
                    self._interrupted.set()
                    await self._send(ws, {"type": "interrupted"})
                    await self._interrupt()
                elif kind == "stop":
                    await self._interrupt()
                    break
        except WebSocketDisconnect:
            pass
        finally:
            await self._interrupt()

    async def _send(self, ws: WebSocket, payload: dict[str, Any]) -> None:
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
        )
        await self._send(
            ws,
            {
                "type": "ready",
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
            await self._interrupt()
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
        pcm = bytes(state.buffer)
        state.buffer = bytearray()
        heard_ms = getattr(self.vad, "heard_ms", 0)
        self.vad.reset()
        if self.stt is None or not pcm or heard_ms < MIN_SPEECH_MS:
            await self._send(ws, {"type": "nothing_heard"})
            return
        # a new utterance ends the running answer first: the shared DB session is used by one
        # coroutine at a time (SQLAlchemy async sessions are not safe for concurrent use)
        await self._interrupt()
        if self._busy_beyond_interrupt:
            await self._send(
                ws,
                {
                    "type": "error",
                    "message": "Still finishing the previous answer — wait a moment or type.",
                    "fallback": "text",
                },
            )
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
        timing = TurnTiming(t_start=time.perf_counter(), stt_ms=stt_ms)
        self._interrupted.clear()
        req = TurnRequest(
            session_id=state.session_id,
            text=text,
            skill_id=state.skill_id,
            conversation_lang=state.lang if state.conversation else None,
            spoken=not state.text_only,
        )
        pending = ""
        done_payload: dict[str, Any] | None = None
        first_token = True
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
                    pending += tok
                    parts = sentences(pending)
                    if len(parts) > 1:
                        for s in parts[:-1]:
                            if speakable(s):
                                await speak_queue.put(speakable(s))
                        pending = parts[-1]
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
                    "message": "The tutor model did not answer. Nothing was changed. Try again.",
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
__all__ = ["VoiceLoop", "prune", "sentences", "speakable", "TurnTiming", "Factory", "AsyncIterator"]
