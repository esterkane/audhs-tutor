"""Audio/video lectures -> timed transcript blocks through a registry STT model (ADR-0010).

The transcriber is a `Transcriber` (sync, runs inside the loader thread). `MlxWhisperTranscriber`
wraps `mlx_whisper` and receives audio as a 16 kHz mono float array, so the model itself never
needs ffmpeg; decoding is done by `converters.find_decoder()` (ffmpeg, else macOS afconvert).
Transcripts are cached under `Settings.transcript_cache_dir` by content hash, so a trust
re-decision or a chunker change never transcribes twice. A caption/transcript file next to the
media always wins (`sidecar_transcript`) — cheaper and usually human-corrected."""

import json
import struct
import time
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from app.knowledge.ingest.captions import Cue, dedupe_rolling, merge_cues
from app.knowledge.ingest.converters import decode_to_wav, decoder_supports, find_decoder
from app.knowledge.ingest.types import Block, RuntimeCallFailed

AUDIO_SUFFIXES = {
    ".mp3", ".m4a", ".m4b", ".aac", ".wav", ".flac", ".ogg", ".oga", ".opus", ".wma", ".aiff",
    ".aif", ".caf", ".amr", ".ac3", ".alac", ".weba",
}  # fmt: skip
# `.ts`/`.mts` are deliberately absent: in a course repo they are TypeScript, not MPEG-TS.
VIDEO_SUFFIXES = {
    ".mp4", ".m4v", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".flv", ".mpg", ".mpeg", ".3gp",
    ".ogv", ".m2ts",
}  # fmt: skip
MEDIA_SUFFIXES = AUDIO_SUFFIXES | VIDEO_SUFFIXES
CAPTION_SUFFIXES = {".vtt", ".srt", ".sbv", ".ass", ".ssa", ".ttml", ".dfxp"}
SNIFFED_SIDECARS = {".json", ".tsv", ".txt"}  # accepted only when they parse as a transcript
CACHE_VERSION = 1
DEFAULT_STT_HINT = (
    "no ready speech-to-text model — pull the model routed for `stt` under Models "
    "(`scripts/ingest.py --capabilities` shows which)"
)


class SttSupportMissing(RuntimeError):
    pass


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    segments: list[Segment]
    language: str | None = None
    model: str = ""
    registry_id: str = ""
    duration_s: float = 0.0
    latency_ms: int = 0
    decoder: str | None = None
    cached: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


class Transcriber(Protocol):
    model: str
    registry_id: str

    def transcribe(self, wav: Path, *, language: str | None = None) -> TranscriptResult: ...


def read_wav_mono16k(path: Path) -> tuple[Any, float]:
    """PCM WAV → float32 array in [-1, 1] plus duration. Requires 16 kHz mono 16-bit (what
    `decode_to_wav` produces); anything else must be decoded first."""
    import numpy as np

    with wave.open(str(path), "rb") as w:
        rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        data = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError(f"WAV must be 16-bit PCM, got {width * 8}-bit")
    audio = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if rate != 16000:
        # linear resample (only reached for WAV input that skipped the decoder)
        n = int(round(len(audio) * 16000 / rate))
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(
            np.float32
        )
    return audio, len(audio) / 16000.0


def wav_is_native(path: Path) -> bool:
    """A PCM WAV of any rate/channels is readable without an external decoder."""
    try:
        with path.open("rb") as f:
            head = f.read(12)
        return len(head) == 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    except OSError:
        return False


class MlxWhisperTranscriber:
    """`mlx_whisper.transcribe` on a local snapshot (registry `local_path`). Import is lazy: the
    package is an optional extra (`uv sync --group stt`)."""

    def __init__(self, model_path: str, *, registry_id: str, model: str | None = None) -> None:
        self.model_path = model_path
        self.registry_id = registry_id
        self.model = model or Path(model_path).name

    def transcribe(self, wav: Path, *, language: str | None = None) -> TranscriptResult:
        try:
            import mlx_whisper
        except ImportError as e:
            raise SttSupportMissing(
                "audio transcription needs the optional `mlx-whisper` package: uv sync --group stt"
            ) from e
        audio, duration = read_wav_mono16k(wav)
        t0 = time.perf_counter()
        out = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self.model_path,
            language=language or None,
            condition_on_previous_text=False,
            verbose=None,
        )
        segs = [
            Segment(float(s["start"]), float(s["end"]), str(s["text"]).strip())
            for s in out.get("segments", [])
            if str(s.get("text", "")).strip()
        ]
        return TranscriptResult(
            segments=segs,
            language=out.get("language"),
            model=self.model,
            registry_id=self.registry_id,
            duration_s=duration,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )


# ----------------------------------------------------------------------------- cache
def _cache_path(cache_dir: Path, content_hash: str) -> Path:
    return cache_dir / f"{content_hash}.json"


def load_cached(cache_dir: Path | None, content_hash: str) -> TranscriptResult | None:
    if cache_dir is None:
        return None
    p = _cache_path(cache_dir, content_hash)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("cache_version") != CACHE_VERSION:
        return None
    return TranscriptResult(
        segments=[Segment(**s) for s in data.get("segments", [])],
        language=data.get("language"),
        model=data.get("model", ""),
        registry_id=data.get("registry_id", ""),
        duration_s=float(data.get("duration_s", 0.0)),
        decoder=data.get("decoder"),
        cached=True,
    )


def save_cached(cache_dir: Path | None, content_hash: str, res: TranscriptResult) -> None:
    if cache_dir is None:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "cache_version": CACHE_VERSION,
        "segments": [asdict(s) for s in res.segments],
        "language": res.language,
        "model": res.model,
        "registry_id": res.registry_id,
        "duration_s": res.duration_s,
        "decoder": res.decoder,
    }
    _cache_path(cache_dir, content_hash).write_text(json.dumps(payload, ensure_ascii=False))


# ----------------------------------------------------------------------------- pipeline
def _is_transcript_file(cand: Path) -> bool:
    """`.json/.txt/.tsv` next to a video is often metadata or a description: accept it as a sidecar
    only when it actually parses as a transcript."""
    from app.knowledge.ingest.transcripts import transcript_cues

    try:
        if cand.stat().st_size > 20_000_000:
            return False
        text = cand.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    try:
        return bool(transcript_cues(text, cand.suffix.lower()))
    except Exception:
        return False


def sidecar_transcript(path: Path) -> Path | None:
    """A caption/transcript next to the media with the same stem (`lecture.mp4` ↔ `lecture.en.vtt`),
    or — inside a Udemy resources lecture folder holding exactly one media file — any caption in
    that folder. Non-caption suffixes count only when they parse as a transcript."""
    stem = path.stem.lower()
    best: Path | None = None
    siblings = sorted(p for p in path.parent.iterdir() if p.is_file())
    for cand in siblings:
        if cand == path:
            continue
        suffix = cand.suffix.lower()
        if suffix not in CAPTION_SUFFIXES and suffix not in SNIFFED_SIDECARS:
            continue
        cstem = cand.stem.lower()
        if not (cstem == stem or cstem.startswith(stem + ".") or cstem.startswith(stem + "_")):
            continue
        if suffix in SNIFFED_SIDECARS and not _is_transcript_file(cand):
            continue
        if best is None or _sidecar_rank(cand) < _sidecar_rank(best):
            best = cand
    if best is None and path.parent.name.lower().startswith("lecture"):
        media_here = [p for p in siblings if p.suffix.lower() in MEDIA_SUFFIXES]
        caps = [c for c in siblings if c.suffix.lower() in (".vtt", ".srt")]
        if len(media_here) == 1 and caps:
            best = min(caps, key=_sidecar_rank)
    return best


def _sidecar_rank(p: Path) -> tuple[int, int, str]:
    order = [".vtt", ".srt", ".sbv", ".ass", ".ssa", ".ttml", ".dfxp", ".tsv", ".json", ".txt"]
    lang = 0 if ".en" in p.stem.lower() else 1
    return (order.index(p.suffix.lower()) if p.suffix.lower() in order else 99, lang, p.name)


def transcribe_media(
    path: Path,
    transcriber: Transcriber | None,
    *,
    content_hash: str,
    cache_dir: Path | None,
    workdir: Path,
    language: str | None = None,
    decoder: str | None = None,
    hint: str = DEFAULT_STT_HINT,
) -> TranscriptResult:
    """Cache → decode → transcribe. Raises `SttSupportMissing` without a transcriber,
    `RuntimeError` naming the decoder problem and `RuntimeCallFailed` when the model call itself
    failed (so the failure is logged as a `model_call` row)."""
    cached = load_cached(cache_dir, content_hash)
    if cached is not None:
        return cached
    if transcriber is None:
        raise SttSupportMissing(hint)
    decoder = decoder if decoder is not None else find_decoder()
    suffix = path.suffix.lower()
    if wav_is_native(path):
        wav, used = path, None
    elif decoder and decoder_supports(decoder, suffix):
        wav = workdir / (path.stem + ".16k.wav")
        decode_to_wav(path, wav, decoder)
        used = decoder
    elif decoder == "afconvert":
        raise RuntimeError(
            f"{suffix} needs ffmpeg (`brew install ffmpeg`); afconvert cannot decode it"
        )
    else:
        raise RuntimeError("no audio decoder found: brew install ffmpeg")
    t0 = time.perf_counter()
    try:
        res = transcriber.transcribe(wav, language=language)
    except SttSupportMissing:
        raise
    except Exception as e:
        raise RuntimeCallFailed(
            task="stt",
            provider="mlx",
            registry_id=transcriber.registry_id,
            model=transcriber.model,
            error=f"{type(e).__name__}: {e}",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ) from e
    res.decoder = used
    if not res.duration_s:
        try:
            res.duration_s = read_wav_mono16k(wav)[1]
        except (OSError, ValueError, wave.Error, struct.error):
            pass
    save_cached(cache_dir, content_hash, res)
    return res


def transcript_to_blocks(res: TranscriptResult) -> list[Block]:
    cues = [Cue(s.start, s.end, s.text) for s in res.segments if s.text.strip()]
    return merge_cues(dedupe_rolling(cues))
