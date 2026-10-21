"""Local CTranslate2 Whisper adapter. Never downloads at inference time."""

import time
from pathlib import Path
from threading import Lock
from typing import Any

from app.knowledge.ingest.media import (
    Segment,
    SttSupportMissing,
    TranscriptResult,
    read_wav_mono16k,
)


class FasterWhisperTranscriber:
    provider = "faster-whisper"

    def __init__(
        self,
        model_path: str,
        *,
        registry_id: str,
        model: str | None = None,
        device: str = "cuda",
        compute_type: str = "float16",
    ) -> None:
        self.model_path = model_path
        self.registry_id = registry_id
        self.model = model or Path(model_path).name
        self.device = device
        self.compute_type = compute_type
        self._runtime: Any = None
        self._lock = Lock()

    def transcribe(self, wav: Path, *, language: str | None = None) -> TranscriptResult:
        local = Path(self.model_path)
        if not local.is_dir() or not all(
            (local / f).is_file() for f in ("config.json", "model.bin", "tokenizer.json")
        ):
            raise SttSupportMissing("CTranslate2 Whisper local snapshot is missing or incomplete")
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise SttSupportMissing("Install the stt-cuda dependency group") from exc
        start = time.perf_counter()
        audio, duration = read_wav_mono16k(wav)
        if not audio.any():
            return TranscriptResult(
                segments=[],
                language=language,
                model=self.model,
                registry_id=self.registry_id,
                duration_s=duration,
                meta={"provider": self.provider},
            )
        with self._lock:
            if self._runtime is None:
                self._runtime = WhisperModel(
                    str(local),
                    device=self.device,
                    compute_type=self.compute_type,
                    local_files_only=True,
                )
            segments, info = self._runtime.transcribe(audio, language=language)
            result = [
                Segment(float(s.start), float(s.end), s.text.strip())
                for s in segments
                if s.text.strip()
            ]
        return TranscriptResult(
            segments=result,
            language=info.language,
            model=self.model,
            registry_id=self.registry_id,
            duration_s=float(info.duration),
            latency_ms=int((time.perf_counter() - start) * 1000),
            meta={"provider": self.provider},
        )
