"""Speech-to-text behind the registry: the MLX Whisper snapshot the ingest pipeline already uses
(`knowledge/ingest/media.MlxWhisperTranscriber`), and `FakeStt` for tests."""

from __future__ import annotations

import asyncio
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.voice.vad import wav_bytes


@dataclass
class SttResult:
    text: str
    language: str | None
    latency_ms: int
    model: str
    registry_id: str


class Stt(Protocol):
    registry_id: str

    async def transcribe(self, pcm16: bytes, *, language: str | None) -> SttResult: ...


class MlxWhisperStt:
    def __init__(self, snapshot_path: str, *, registry_id: str) -> None:
        from app.knowledge.ingest.media import MlxWhisperTranscriber

        self._t = MlxWhisperTranscriber(snapshot_path, registry_id=registry_id)
        self.registry_id = registry_id

    async def transcribe(self, pcm16: bytes, *, language: str | None) -> SttResult:
        # the recording is written to a temp file only for the duration of the call and deleted
        with tempfile.TemporaryDirectory(prefix="audhs-voice-") as d:
            path = Path(d) / "utterance.wav"
            path.write_bytes(wav_bytes(pcm16))
            t0 = time.perf_counter()
            res = await asyncio.to_thread(self._t.transcribe, path, language=language)
        text = " ".join(s.text for s in res.segments).strip()
        return SttResult(
            text=text,
            language=res.language,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            model=res.model,
            registry_id=self.registry_id,
        )


class FakeStt:
    registry_id = "fake-stt"

    def __init__(self, text: str = "what is attention", *, fail_times: int = 0) -> None:
        self.text = text
        self.fail_times = fail_times
        self.heard: list[float] = []

    async def transcribe(self, pcm16: bytes, *, language: str | None) -> SttResult:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("fake stt failure")
        self.heard.append(len(pcm16) / 2 / 16_000)
        return SttResult(
            text=self.text if pcm16.strip(b"\x00") else "",
            language=language or "en",
            latency_ms=1,
            model="fake-whisper",
            registry_id=self.registry_id,
        )
