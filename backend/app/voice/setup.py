"""Voice setup lifecycle (P9): inspect readiness → explicit install (registry pull jobs) → verify the
runtime actually loads → test with a recording → explicitly activate. Reading readiness never
downloads or starts anything; activation is a preference the learner sets and can unset."""

from __future__ import annotations

import io
import struct
import time
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import ModelRegistry
from app.db.traces import ModelCallRecord, write_model_call
from app.kernel import preferences
from app.models_ai.manage import KOKORO_SETUP
from app.models_ai.provider import TaskClass
from app.models_ai.routing import Router
from app.voice.stt import FakeStt, MlxWhisperStt, Stt
from app.voice.tts import (
    LANG_TO_KOKORO,
    FakeTts,
    KokoroClient,
    Tts,
    kokoro_reachable,
    kokoro_supports,
)
from app.voice.vad import EnergyVad, Vad, vad_for

MAX_TEST_SECONDS = 20.0
MIN_TEST_SECONDS = 0.5
MAX_TEST_BYTES = 4 * 1024 * 1024 + 1024
VAD_ROLE = "vad"


def stt_id(settings: Settings) -> str:
    return Router(settings.routing_profile).chain_for(TaskClass.STT)[0]


def tts_id(settings: Settings) -> str:
    return Router(settings.routing_profile).chain_for(TaskClass.TTS)[0]


async def vad_row(db: AsyncSession) -> ModelRegistry | None:
    return (
        (await db.execute(select(ModelRegistry).where(ModelRegistry.role == VAD_ROLE)))
        .scalars()
        .first()
    )


@dataclass
class Component:
    ready: bool
    status: str
    detail: str
    action: str | None = None


@dataclass
class Readiness:
    stt: Component
    tts: Component
    vad: Component
    tools: Component
    activated: bool
    retain_audio: bool
    retention_days: int
    voice: str
    can_activate: bool
    stt_id: str = ""
    tts_id: str = ""
    vad_id: str | None = None
    conversation_lang: str = ""
    conversation_lang_supported: bool = True
    notes: list[str] = field(default_factory=list)

    def dict(self) -> dict[str, Any]:
        return asdict(self)


def _importable(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None


async def readiness(db: AsyncSession, settings: Settings, learner_id: str) -> Readiness:
    """Each component: ready / status / literal detail / the one step that fixes it. Never installs."""
    sid, tid = stt_id(settings), tts_id(settings)
    stt_row = await db.get(ModelRegistry, sid)
    tts_row = await db.get(ModelRegistry, tid)
    vrow = await vad_row(db)
    # STT: registry row ready + snapshot present + package importable
    if stt_row is None:
        stt = Component(False, "unknown", "whisper row missing from the registry", "reload Models")
    elif stt_row.status != "ready" or not stt_row.local_path:
        stt = Component(
            False,
            stt_row.status,
            "MLX Whisper snapshot not downloaded",
            f"Models › pull {sid} (about 1.6 GB, mlx-community, MIT)",
        )
    elif not _importable("mlx_whisper"):
        stt = Component(
            False,
            "package missing",
            "the snapshot is there but the optional `mlx-whisper` package is not installed",
            "run `uv sync --group stt` in backend/, then restart the backend",
        )
    else:
        stt = Component(True, "ready", f"MLX Whisper at {stt_row.local_path}")
    # TTS: the persistent Kokoro server answers
    # readiness is a pure read: the registry status is owned by Models (seed/pull), not by a GET
    reachable = await kokoro_reachable(settings.kokoro_url)
    if reachable:
        tts = Component(True, "ready", f"Kokoro server answering at {settings.kokoro_url}")
    else:
        tts = Component(
            False,
            tts_row.status if tts_row else "unknown",
            f"no Kokoro server at {settings.kokoro_url}",
            KOKORO_SETUP,
        )
    # VAD: Silero when installed, energy detector otherwise (always usable)
    vad_path = Path(vrow.local_path) if vrow and vrow.local_path else None
    _, vad_note = vad_for(vad_path)
    vad = (
        Component(True, "ready", "Silero VAD (ONNX)")
        if vad_note is None
        else Component(
            True,
            "fallback",
            vad_note,
            f"Models › pull {vrow.id if vrow else 'the VAD model'} (2 MB, MIT) for better speech/silence detection",
        )
    )
    # tools: audio conversion for ingest is not needed for the loop (PCM comes from the browser)
    tools = Component(True, "ready", "browser microphone → PCM16 16 kHz; no ffmpeg needed")
    prefs = {
        k: await preferences.get(db, learner_id, k)
        for k in (
            "voice.enabled",
            "voice.retain_audio",
            "voice.retention_days",
            "voice.voice",
            "voice.conversation_lang",
        )
    }
    activated = bool(prefs.get("voice.enabled"))
    conv_lang = str(prefs.get("voice.conversation_lang") or "")
    conv_ok = kokoro_supports(conv_lang or None)
    notes: list[str] = []
    if activated and not (stt.ready and tts.ready):
        notes.append("voice is activated but a component is missing: turns fall back to text")
    if conv_lang and not conv_ok:
        notes.append(
            f"the Kokoro voices do not speak '{conv_lang}' (supported: {', '.join(sorted(LANG_TO_KOKORO))}); "
            "conversation practice in that language stays text-only"
        )
    return Readiness(
        stt=stt,
        tts=tts,
        vad=vad,
        tools=tools,
        activated=activated,
        retain_audio=bool(prefs.get("voice.retain_audio")),
        retention_days=int(prefs.get("voice.retention_days") or 7),
        voice=str(prefs.get("voice.voice") or ""),
        can_activate=stt.ready and tts.ready,
        stt_id=sid,
        tts_id=tid,
        vad_id=vrow.id if vrow else None,
        conversation_lang=conv_lang,
        conversation_lang_supported=conv_ok,
        notes=notes,
    )


# ----------------------------------------------------------------------------- adapters
def stt_for(settings: Settings, stt_row: ModelRegistry | None) -> Stt | None:
    if stt_row is None or stt_row.status != "ready" or not stt_row.local_path:
        return None
    if not _importable("mlx_whisper"):
        return None
    return MlxWhisperStt(stt_row.local_path, registry_id=stt_row.id)


def tts_for(settings: Settings, reachable: bool) -> Tts | None:
    return KokoroClient(settings.kokoro_url, registry_id=tts_id(settings)) if reachable else None


async def adapters(
    db: AsyncSession, settings: Settings, overrides: dict[str, Any] | None
) -> tuple[Stt | None, Tts | None, Vad]:
    """Real adapters from the registry, or the test overrides on `app.state.voice_overrides`."""
    if overrides:
        return (
            overrides.get("stt", FakeStt()),
            overrides.get("tts", FakeTts()),
            overrides.get("vad", EnergyVad()),
        )
    stt_row = await db.get(ModelRegistry, stt_id(settings))
    vrow = await vad_row(db)
    vad, _ = vad_for(Path(vrow.local_path) if vrow and vrow.local_path else None)
    return (
        stt_for(settings, stt_row),
        tts_for(settings, await kokoro_reachable(settings.kokoro_url)),
        vad,
    )


# ----------------------------------------------------------------------------- verify / test
def parse_test_wav(data: bytes) -> bytes:
    """Validate an uploaded test recording (mono PCM16 16 kHz, 0.5–20 s) → raw PCM16."""
    if len(data) > MAX_TEST_BYTES:
        raise ValueError("recording too large: at most 20 seconds")
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != 16_000:
                raise ValueError("recording must be mono 16-bit 16 kHz WAV")
            frames = w.getnframes()
            seconds = frames / 16_000
            if not MIN_TEST_SECONDS <= seconds <= MAX_TEST_SECONDS:
                raise ValueError("record between 0.5 and 20 seconds")
            return w.readframes(frames)
    except (wave.Error, EOFError, struct.error) as e:
        raise ValueError("not a WAV file") from e


async def verify_stt(
    db: AsyncSession, stt: Stt, pcm16: bytes, *, learner_id: str, language: str | None
) -> dict[str, Any]:
    """Run the real STT once on a recording that is discarded afterwards; logged as a model_call."""
    t0 = time.perf_counter()
    try:
        res = await stt.transcribe(pcm16, language=language)
    except Exception as e:
        await write_model_call(
            db,
            ModelCallRecord(
                provider="mlx",
                model=stt.registry_id,
                registry_id=stt.registry_id,
                task="stt",
                ok=False,
                error=str(e)[:300],
                outcome="error",
                usage_source="unavailable",
                cost_status="free",
                latency_ms=int((time.perf_counter() - t0) * 1000),
                learner_id=learner_id,
                metadata={"purpose": "voice-setup-test"},
            ),
        )
        raise
    await write_model_call(
        db,
        ModelCallRecord(
            provider="mlx",
            model=res.model,
            registry_id=res.registry_id,
            task="stt",
            latency_ms=res.latency_ms,
            usage_source="unavailable",
            cost_status="free",
            learner_id=learner_id,
            metadata={"purpose": "voice-setup-test", "seconds": len(pcm16) / 32_000},
        ),
    )
    return {"text": res.text, "language": res.language, "latency_ms": res.latency_ms}


async def verify_tts(
    db: AsyncSession, tts: Tts, *, learner_id: str, voice: str, lang: str | None
) -> dict[str, Any]:
    """Synthesize one fixed sentence; returns PCM16 24 kHz bytes + timing; logged as a model_call."""
    sentence = "The local voice is ready. This sentence was spoken on this machine."
    t0 = time.perf_counter()
    pcm = bytearray()
    first_ms: int | None = None
    rate = 24_000
    try:
        async for chunk in tts.stream(sentence, voice=voice, lang=lang):
            if first_ms is None:
                first_ms = chunk.first_audio_ms or int((time.perf_counter() - t0) * 1000)
            rate = chunk.sample_rate
            pcm += chunk.pcm16
    except Exception as e:
        await write_model_call(
            db,
            ModelCallRecord(
                provider="kokoro",
                model=tts.model,
                registry_id=tts.registry_id,
                task="tts",
                ok=False,
                error=str(e)[:300],
                outcome="error",
                usage_source="unavailable",
                cost_status="free",
                learner_id=learner_id,
                metadata={"purpose": "voice-setup-test"},
            ),
        )
        raise
    await write_model_call(
        db,
        ModelCallRecord(
            provider="kokoro",
            model=tts.model,
            registry_id=tts.registry_id,
            task="tts",
            latency_ms=int((time.perf_counter() - t0) * 1000),
            tokens_in=len(sentence.split()),
            usage_source="estimated",
            cost_status="free",
            learner_id=learner_id,
            metadata={"purpose": "voice-setup-test", "voice": voice},
        ),
    )
    return {
        "pcm16": bytes(pcm),
        "sample_rate": rate,
        "first_audio_ms": first_ms or 0,
        "seconds": len(pcm) / 2 / rate,
    }


async def set_activation(
    db: AsyncSession, learner_id: str, *, enabled: bool, ready: Readiness
) -> None:
    """Activation is separate from installation and needs both components ready."""
    if enabled and not ready.can_activate:
        raise ValueError(
            "voice cannot be activated yet: "
            + "; ".join(
                f"{n}: {c.detail}"
                for n, c in (("stt", ready.stt), ("tts", ready.tts))
                if not c.ready
            )
        )
    await preferences.set_pref(db, learner_id, "voice.enabled", enabled, origin="explicit")


__all__ = [
    "Readiness",
    "readiness",
    "adapters",
    "parse_test_wav",
    "verify_stt",
    "verify_tts",
    "set_activation",
]
