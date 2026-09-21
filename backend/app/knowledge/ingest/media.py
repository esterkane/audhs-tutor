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
    source_format: str | None = None  # what the input was (e.g. "pcm24 48000 Hz 2ch")
    meta: dict[str, Any] = field(default_factory=dict)


# ----------------------------------------------------------------------------- WAV normalisation
MAX_WAV_BYTES = 1_500_000_000  # above this the file goes to ffmpeg/afconvert or must be split
_BLOCK_FRAMES = 600 * 48_000  # normalisation works in ~10-minute blocks: memory stays bounded
_RESAMPLE_PAD = 16_384  # input samples of overlap on each block edge (> the polyphase filter)
_WAVE_FORMAT_PCM = 1
_WAVE_FORMAT_IEEE_FLOAT = 3
_WAVE_FORMAT_EXTENSIBLE = 0xFFFE
_INPROCESS_DEPTHS = {(_WAVE_FORMAT_PCM, 8), (_WAVE_FORMAT_PCM, 16), (_WAVE_FORMAT_PCM, 24)}
_INPROCESS_DEPTHS |= {(_WAVE_FORMAT_PCM, 32), (_WAVE_FORMAT_IEEE_FLOAT, 32)}
_INPROCESS_DEPTHS |= {(_WAVE_FORMAT_IEEE_FLOAT, 64)}


@dataclass
class WavInfo:
    """What a WAV container holds, read from its `fmt ` chunk (never trusted for more than that)."""

    format_tag: int
    channels: int
    rate: int
    bits: int
    frames: int

    @property
    def duration_s(self) -> float:
        return self.frames / self.rate if self.rate else 0.0

    @property
    def block_bytes(self) -> int:
        return self.channels * self.bits // 8

    @property
    def in_process(self) -> bool:
        """Can `normalize_wav` decode it here (PCM/float at a known depth)?"""
        return (self.format_tag, self.bits) in _INPROCESS_DEPTHS

    @property
    def label(self) -> str:
        if self.format_tag == _WAVE_FORMAT_PCM:
            kind = f"pcm{self.bits}"
        elif self.format_tag == _WAVE_FORMAT_IEEE_FLOAT:
            kind = f"float{self.bits}"
        else:
            kind = f"tag{self.format_tag:#x}/{self.bits}bit"
        return f"{kind} {self.rate} Hz {self.channels}ch"


def probe_wav(path: Path) -> tuple[WavInfo, int, int]:
    """Parse the RIFF/WAVE header: `(info, data_offset, data_size)`. Handles PCM, IEEE float and
    WAVE_FORMAT_EXTENSIBLE (the 24-bit / multichannel exports course authors produce), which the
    stdlib `wave` module refuses. Raises `ValueError` for anything that is not a WAV."""
    with path.open("rb") as f:
        head = f.read(12)
        if len(head) < 12 or head[:4] != b"RIFF" or head[8:12] != b"WAVE":
            raise ValueError("not a RIFF/WAVE file")
        fmt: tuple[int, int, int, int, int] | None = None
        data: tuple[int, int] | None = None
        pos = 12
        size_total = path.stat().st_size
        while pos + 8 <= size_total and (fmt is None or data is None):
            f.seek(pos)
            chunk = f.read(8)
            if len(chunk) < 8:
                break
            cid, csize = chunk[:4], struct.unpack("<I", chunk[4:8])[0]
            if cid == b"fmt ":
                body = f.read(min(csize, 64))
                if len(body) < 16:
                    raise ValueError("WAV fmt chunk too short")
                tag, channels, rate, _byte_rate, block_align, bits = struct.unpack(
                    "<HHIIHH", body[:16]
                )
                if tag == _WAVE_FORMAT_EXTENSIBLE:
                    if len(body) < 40:
                        raise ValueError("malformed WAVE_FORMAT_EXTENSIBLE header")
                    tag = struct.unpack("<H", body[24:26])[0]  # sub-format GUID, first two bytes
                fmt = (tag, channels, rate, bits, block_align)
            elif cid == b"data":
                if csize == 0xFFFFFFFF or pos + 8 + csize > size_total:
                    csize = size_total - pos - 8  # streaming writers leave the size unset
                data = (pos + 8, csize)
            pos += 8 + csize + (csize & 1)
        if fmt is None or data is None:
            raise ValueError("WAV without fmt/data chunks")
        tag, channels, rate, bits, block_align = fmt
        if channels < 1 or rate < 1 or bits < 1:
            raise ValueError("WAV fmt chunk is inconsistent")
        # whole-byte PCM/float: derive the frame size, never trust block_align; compressed
        # formats (4-bit ADPCM …) keep the header's block_align only to estimate the duration
        block = channels * bits // 8 if bits >= 8 and bits % 8 == 0 else max(block_align, 1)
        frames = data[1] // block
        return WavInfo(tag, channels, rate, bits, frames), data[0], data[1]


def _samples_to_float(data: bytes, info: WavInfo) -> Any:
    import numpy as np

    if info.format_tag == _WAVE_FORMAT_IEEE_FLOAT:
        if info.bits == 32:
            return np.frombuffer(data, dtype="<f4").astype(np.float32)
        if info.bits == 64:
            return np.frombuffer(data, dtype="<f8").astype(np.float32)
        raise RuntimeError(f"{info.bits}-bit float WAV needs ffmpeg (`brew install ffmpeg`)")
    if info.format_tag != _WAVE_FORMAT_PCM:
        raise RuntimeError(
            f"WAV {info.label} (compressed or µ-law) needs ffmpeg (`brew install ffmpeg`)"
        )
    if info.bits == 8:
        return (np.frombuffer(data, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    if info.bits == 16:
        return np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    if info.bits == 24:
        raw = np.frombuffer(data, dtype=np.uint8)
        n = len(raw) // 3
        b = raw[: n * 3].reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        return v.astype(np.float32) / 8388608.0
    if info.bits == 32:
        return np.frombuffer(data, dtype="<i4").astype(np.float32) / 2147483648.0
    raise RuntimeError(f"{info.bits}-bit PCM WAV needs ffmpeg (`brew install ffmpeg`)")


def _resampler(rate: int, target: int = 16000) -> tuple[int, int, Any]:
    """`(up, down, resample_poly)` — polyphase resampling with an anti-aliasing low-pass. scipy
    ships with the `stt` group (mlx-whisper depends on it); without it we refuse rather than
    hand Whisper an aliased signal."""
    import math

    try:
        from scipy.signal import resample_poly
    except ImportError as e:
        raise RuntimeError(
            "resampling needs scipy (uv sync --group stt) — or transcode with ffmpeg"
        ) from e
    g = math.gcd(rate, target)
    return target // g, rate // g, resample_poly


def normalize_wav(src: Path, dst: Path) -> WavInfo:
    """Any PCM/float WAV (8/16/24/32-bit int, 32/64-bit float, any rate, any channel count,
    extensible headers) → 16 kHz mono 16-bit PCM at `dst`, which is what the STT adapter reads.
    The source is only read, in ~10-minute blocks: peak memory is a few hundred MB regardless of
    the file's length (block-wise downmix + overlap-save polyphase resampling). Compressed WAV
    variants and oversized files are refused with the ffmpeg hint (a retryable outcome) instead
    of being handed to the model unchanged; `transcribe_media` tries the external decoder first."""
    import numpy as np

    info, offset, size = probe_wav(src)
    if not info.in_process:
        raise RuntimeError(
            f"WAV {info.label} (compressed or µ-law) needs ffmpeg (`brew install ffmpeg`)"
        )
    if size > MAX_WAV_BYTES:
        raise RuntimeError(
            f"WAV data of {size // 1_000_000} MB exceeds the {MAX_WAV_BYTES // 1_000_000} MB "
            "normalisation bound: transcode it with ffmpeg (`brew install ffmpeg`) or split it"
        )
    block_bytes = info.block_bytes
    total_frames = size // block_bytes
    up, down, resample_poly = _resampler(info.rate) if info.rate != 16000 else (1, 1, None)
    pad = _RESAMPLE_PAD if resample_poly is not None else 0
    carry = np.zeros(0, dtype=np.float32)  # the last `pad` input samples of the previous block
    done_frames = 0
    with src.open("rb") as f, wave.open(str(dst), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        f.seek(offset)
        while done_frames < total_frames:
            n = min(_BLOCK_FRAMES, total_frames - done_frames)
            data = f.read(n * block_bytes)
            if len(data) < block_bytes:
                break
            n = len(data) // block_bytes
            audio = _samples_to_float(data[: n * block_bytes], info)
            if info.channels > 1:
                audio = audio.reshape(-1, info.channels).mean(axis=1, dtype=np.float32)
            audio = np.nan_to_num(audio, nan=0.0, posinf=1.0, neginf=-1.0)
            done_frames += n
            if resample_poly is None:
                out = audio
            else:
                # overlap-save: resample carry+block, keep exactly the output samples that
                # belong to this block (index math on the un-padded stream), stash the tail
                x = np.concatenate([carry, audio]) if len(carry) else audio
                y = np.asarray(resample_poly(x, up, down), dtype=np.float32)
                start_out = (done_frames - n) * up // down
                lead = len(carry) * up // down
                # the whole stream resamples to ceil(frames*up/down) samples; each block emits
                # exactly its share so the pieces line up and the total length is exact
                end_out = (
                    done_frames * up // down
                    if done_frames < total_frames
                    else -(-total_frames * up // down)
                )
                out = y[lead : lead + (end_out - start_out)]
                carry = audio[-pad:] if len(audio) >= pad else audio
            pcm = (np.clip(np.rint(out * 32767.0), -32768, 32767)).astype("<i2").tobytes()
            w.writeframes(pcm)
    return info


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


def load_cached(
    cache_dir: Path | None,
    content_hash: str,
    *,
    registry_id: str | None = None,
    model: str | None = None,
) -> TranscriptResult | None:
    """A cached transcript is reused only for the same model identity when one is given: after a
    model change the old text must not masquerade as the new model's output."""
    if cache_dir is None:
        return None
    p = _cache_path(cache_dir, content_hash)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or data.get("cache_version") != CACHE_VERSION:
        return None
    if registry_id is not None and data.get("registry_id") != registry_id:
        return None
    if model is not None and data.get("model") != model:
        return None
    try:
        return TranscriptResult(
            segments=[Segment(**s) for s in data.get("segments", [])],
            language=data.get("language"),
            model=data.get("model", ""),
            registry_id=data.get("registry_id", ""),
            duration_s=float(data.get("duration_s", 0.0)),
            decoder=data.get("decoder"),
            source_format=data.get("source_format"),
            cached=True,
        )
    except (TypeError, ValueError):
        return None  # corrupted entry: transcribe again and overwrite it


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
        "source_format": res.source_format,
    }
    target = _cache_path(cache_dir, content_hash)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False))
    tmp.replace(target)


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
    use_cache: bool = True,
) -> TranscriptResult:
    """Cache → normalise/decode → transcribe. Raises `SttSupportMissing` without a transcriber,
    `RuntimeError` naming the decoder problem and `RuntimeCallFailed` when the model call itself
    failed (so the failure is logged as a `model_call` row). A cached transcript is used only
    when it came from the same model (or when no model is available to redo it)."""
    if use_cache:
        cached = load_cached(
            cache_dir,
            content_hash,
            registry_id=transcriber.registry_id if transcriber is not None else None,
            model=transcriber.model if transcriber is not None else None,
        )
        if cached is not None:
            return cached
    if transcriber is None:
        raise SttSupportMissing(hint)
    decoder = decoder if decoder is not None else find_decoder()
    suffix = path.suffix.lower()
    source_format: str | None = None
    if wav_is_native(path):
        # a PCM/float WAV is normalised here (24-bit, stereo, 48 kHz, extensible headers) — the
        # STT adapter only ever sees 16 kHz mono 16-bit and the original bytes are untouched;
        # anything else in a WAV container (compressed, oversized) goes to the external decoder
        # when one is installed, exactly like an mp3 would
        info, _off, size = probe_wav(path)
        wav = workdir / (path.stem + ".16k.wav")
        if info.in_process and size <= MAX_WAV_BYTES:
            normalize_wav(path, wav)
            used = "wav-normalise"
            source_format = info.label
        elif decoder and decoder_supports(decoder, ".wav"):
            decode_to_wav(path, wav, decoder)
            used = decoder
            source_format = f"{info.label} via {decoder}"
        else:
            raise RuntimeError(
                f"WAV {info.label} ({size // 1_000_000} MB) needs ffmpeg (`brew install ffmpeg`)"
            )
    elif decoder and decoder_supports(decoder, suffix):
        wav = workdir / (path.stem + ".16k.wav")
        decode_to_wav(path, wav, decoder)
        used = decoder
        source_format = f"{suffix.lstrip('.')} via {decoder}"
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
    res.source_format = source_format
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
