"""Text-to-speech behind the registry: `KokoroClient` talks to the persistent Kokoro-82M server
(`KOKORO_URL`, OpenAI-compatible `/v1/audio/speech`, PCM out) and `FakeTts` renders silence for
tests. Every synthesis is logged as a `model_call` by the caller (registry id `kokoro-82m`)."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import httpx

TTS_SAMPLE_RATE = 24_000
MAX_TTS_CHARS = 1200
# Kokoro-82M v1 language codes (a = American English, b = British, e Spanish, f French, h Hindi,
# i Italian, j Japanese, p Portuguese, z Chinese). German is NOT supported by the v1 voices.
LANG_TO_KOKORO: dict[str, str] = {
    "en": "a",
    "en-gb": "b",
    "es": "e",
    "fr": "f",
    "hi": "h",
    "it": "i",
    "ja": "j",
    "pt": "p",
    "zh": "z",
}


def kokoro_supports(lang: str | None) -> bool:
    return lang is None or lang.lower() in LANG_TO_KOKORO


@dataclass
class TtsChunk:
    pcm16: bytes
    sample_rate: int
    first_audio_ms: int | None = None  # set on the first chunk of an utterance


class Tts(Protocol):
    name: str
    model: str
    registry_id: str

    def stream(self, text: str, *, voice: str, lang: str | None) -> AsyncIterator[TtsChunk]: ...

    async def voices(self) -> list[str]: ...


async def kokoro_reachable(base_url: str, *, timeout_s: float = 2.0) -> bool:
    """True when the persistent Kokoro server answers its voices listing. Never starts anything."""
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.get(f"{base_url.rstrip('/')}/v1/audio/voices")
            return r.status_code == 200
    except httpx.HTTPError:
        return False


class KokoroClient:
    name = "kokoro"

    def __init__(
        self,
        base_url: str,
        *,
        model: str = "kokoro",
        registry_id: str = "kokoro-82m",
        timeout_s: float = 30.0,
    ) -> None:
        self.base = base_url.rstrip("/")
        self.model = model
        self.registry_id = registry_id
        self.timeout_s = timeout_s

    async def voices(self) -> list[str]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{self.base}/v1/audio/voices")
            r.raise_for_status()
            data = r.json()
        voices = data.get("voices") if isinstance(data, dict) else data
        return [str(v) for v in (voices or [])]

    async def stream(self, text: str, *, voice: str, lang: str | None) -> AsyncIterator[TtsChunk]:
        text = text.strip()[:MAX_TTS_CHARS]
        if not text:
            return
        t0 = time.perf_counter()
        first = True
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            async with client.stream(
                "POST",
                f"{self.base}/v1/audio/speech",
                json={
                    "model": self.model,
                    "input": text,
                    "voice": voice,
                    "response_format": "pcm",
                    "stream": True,
                    **(
                        {"lang_code": LANG_TO_KOKORO[lang.lower()]}
                        if lang and kokoro_supports(lang)
                        else {}
                    ),
                },
            ) as r:
                r.raise_for_status()
                async for chunk in r.aiter_bytes(chunk_size=9600):
                    if not chunk:
                        continue
                    yield TtsChunk(
                        pcm16=chunk,
                        sample_rate=TTS_SAMPLE_RATE,
                        first_audio_ms=int((time.perf_counter() - t0) * 1000) if first else None,
                    )
                    first = False


class FakeTts:
    """Silence at 24 kHz, ~ 60 ms of audio per word; `fail_times` scripts failures."""

    name = "fake"
    model = "fake-tts"
    registry_id = "fake-tts"

    def __init__(self, *, fail_times: int = 0, delay_s: float = 0.0) -> None:
        self.fail_times = fail_times
        self.delay_s = delay_s
        self.spoken: list[str] = []

    async def voices(self) -> list[str]:
        return ["af_heart"]

    async def stream(self, text: str, *, voice: str, lang: str | None) -> AsyncIterator[TtsChunk]:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise httpx.ConnectError("fake tts down")
        self.spoken.append(text)
        words = max(1, len(text.split()))
        if self.delay_s:
            import asyncio

            await asyncio.sleep(self.delay_s)
        n = int(0.06 * words * TTS_SAMPLE_RATE)
        yield TtsChunk(pcm16=b"\x00\x00" * n, sample_rate=TTS_SAMPLE_RATE, first_audio_ms=1)
