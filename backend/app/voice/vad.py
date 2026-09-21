"""Voice activity detection on 16 kHz mono PCM16 frames.

`EnergyVad` needs nothing installed: RMS over a frame against an adaptive noise floor, speech ends
after `silence_ms` of quiet following speech. `SileroVad` uses the ONNX model when the registry
row `silero-vad` is ready and `onnxruntime` is importable; otherwise the energy detector is the
fallback and the readiness report says so. Both are deterministic given the same frames."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

SAMPLE_RATE = 16_000


def rms(pcm16: bytes) -> float:
    n = len(pcm16) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm16[: n * 2])
    return math.sqrt(sum(s * s for s in samples) / n) / 32768.0


class Vad(Protocol):
    name: str

    def feed(self, pcm16: bytes) -> str: ...  # "silence" | "speech" | "end"

    def reset(self) -> None: ...


@dataclass
class EnergyVad:
    """Adaptive energy detector: speech when RMS > max(floor × ratio, min_speech); `end` after
    `silence_ms` of quiet once speech was heard. `heard_ms` counts speech time for the
    empty/noisy-input rule."""

    name: str = "energy"
    ratio: float = 3.0
    min_speech: float = 0.015
    silence_ms: int = 700
    min_speech_ms: int = 300
    floor: float = 0.005
    in_speech: bool = False
    heard_ms: int = 0
    quiet_ms: int = 0
    _frames: int = field(default=0, repr=False)

    def feed(self, pcm16: bytes) -> str:
        ms = len(pcm16) // 2 * 1000 // SAMPLE_RATE
        level = rms(pcm16)
        threshold = max(self.floor * self.ratio, self.min_speech)
        if level > threshold:
            self.in_speech = True
            self.heard_ms += ms
            self.quiet_ms = 0
            return "speech"
        # noise floor adapts slowly on quiet frames only
        self._frames += 1
        self.floor = self.floor * 0.95 + level * 0.05
        if self.in_speech:
            self.quiet_ms += ms
            if self.quiet_ms >= self.silence_ms:
                return "end"
            return "speech"
        return "silence"

    def reset(self) -> None:
        self.in_speech = False
        self.heard_ms = 0
        self.quiet_ms = 0


class SileroVad:
    """Silero VAD v5 ONNX (`snakers4/silero-vad`). Import is lazy; construction fails loudly when
    the model file or onnxruntime is missing so the caller falls back to `EnergyVad`."""

    name = "silero"

    def __init__(self, model_path: Path, *, threshold: float = 0.5, silence_ms: int = 700) -> None:
        import numpy as np
        import onnxruntime as ort

        self._np = np
        self._sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self.threshold = threshold
        self.silence_ms = silence_ms
        self.in_speech = False
        self.heard_ms = 0
        self.quiet_ms = 0
        self._buf = b""

    def _prob(self, chunk: bytes) -> float:
        np = self._np
        x = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
        out, self._state = self._sess.run(
            None,
            {
                "input": x.reshape(1, -1),
                "state": self._state,
                "sr": np.array(SAMPLE_RATE, dtype=np.int64),
            },
        )[:2]
        return float(out[0][0])

    def feed(self, pcm16: bytes) -> str:
        self._buf += pcm16
        status = "silence" if not self.in_speech else "speech"
        while len(self._buf) >= 1024:  # 512 samples = 32 ms windows
            chunk, self._buf = self._buf[:1024], self._buf[1024:]
            if self._prob(chunk) >= self.threshold:
                self.in_speech = True
                self.heard_ms += 32
                self.quiet_ms = 0
                status = "speech"
            elif self.in_speech:
                self.quiet_ms += 32
                status = "end" if self.quiet_ms >= self.silence_ms else "speech"
        return status

    def reset(self) -> None:
        self.in_speech = False
        self.heard_ms = 0
        self.quiet_ms = 0
        self._buf = b""


def vad_for(model_path: Path | None) -> tuple[Vad, str | None]:
    """The best available detector and, when Silero is not usable, the reason."""
    if model_path is not None and model_path.is_file():
        try:
            return SileroVad(model_path), None
        except Exception as e:  # missing onnxruntime, corrupt file
            return EnergyVad(), f"silero-vad unusable ({type(e).__name__}); energy detector in use"
    return EnergyVad(), "silero-vad not installed; energy detector in use"


def pcm16_seconds(pcm16: bytes) -> float:
    return len(pcm16) / 2 / SAMPLE_RATE


def wav_bytes(pcm16: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    """A WAV container around PCM16 mono (what the STT adapters read)."""
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm16)
    return buf.getvalue()


def silence(seconds: float, sample_rate: int = SAMPLE_RATE) -> bytes:
    return b"\x00\x00" * int(seconds * sample_rate)


def tone(seconds: float, *, freq: float = 440.0, amplitude: float = 0.3) -> bytes:
    """A synthetic 'voice' for tests and the spike: never a real microphone benchmark."""
    n = int(seconds * SAMPLE_RATE)
    return struct.pack(
        f"<{n}h",
        *(
            int(amplitude * 32767 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
            for i in range(n)
        ),
    )


__all__: list[str] = [
    "EnergyVad",
    "SileroVad",
    "Vad",
    "vad_for",
    "wav_bytes",
    "silence",
    "tone",
    "pcm16_seconds",
    "rms",
]
_: Any = None
