#!/usr/bin/env python3
"""Isolated voice spike + readiness diagnostics (P9). Runs nothing that is not installed and
downloads nothing; prints what is missing and the exact step that fixes it.

  spike_voice.py                 readiness only
  spike_voice.py --stt FILE.wav  transcribe one mono 16 kHz WAV with the registry's MLX Whisper snapshot
  spike_voice.py --tts "text"    synthesize one sentence with the Kokoro server, write spike_tts.wav
  spike_voice.py --mic 5         record 5 s from the default microphone (needs `sounddevice`), then STT

Temporary recordings are deleted; `--keep` writes them next to this script instead.
"""

import argparse
import asyncio
import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.models_ai.factory import mlx_cached  # noqa: E402
from app.models_ai.routing import load_profiles  # noqa: E402
from app.voice.tts import KokoroClient, kokoro_reachable  # noqa: E402
from app.voice.vad import wav_bytes  # noqa: E402


def readiness() -> dict[str, object]:
    s = get_settings()
    stt_entry = next(
        e for e in load_profiles()["registry_defaults"] if e["id"] == "whisper-large-v3-turbo"
    )
    snap = mlx_cached(s.models_dir_resolved, str(stt_entry["repo_id"]))
    kokoro = asyncio.run(kokoro_reachable(s.kokoro_url))
    return {
        "stt_snapshot": bool(snap),
        "stt_package": importlib.util.find_spec("mlx_whisper") is not None,
        "tts_server": kokoro,
        "tts_url": s.kokoro_url,
        "silero_vad": (s.models_dir_resolved / "onnx" / "silero-vad" / "silero_vad.onnx").is_file(),
        "onnxruntime": importlib.util.find_spec("onnxruntime") is not None,
        "sounddevice": importlib.util.find_spec("sounddevice") is not None,
        "fixes": {
            "stt_snapshot": "make models args='pull whisper-large-v3-turbo'",
            "stt_package": "cd backend && uv sync --group stt",
            "tts_server": "start the Kokoro server (see docs/slices/voice-setup.md), set KOKORO_URL",
            "silero_vad": "make models args='pull silero-vad' (optional; energy VAD otherwise)",
            "sounddevice": "uv pip install sounddevice (optional; only for --mic)",
        },
    }


async def run_stt(wav: Path) -> None:
    from app.voice.stt import MlxWhisperStt

    s = get_settings()
    entry = next(
        e for e in load_profiles()["registry_defaults"] if e["id"] == "whisper-large-v3-turbo"
    )
    from app.models_ai.factory import mlx_snapshot_dir

    path = mlx_snapshot_dir(s.models_dir_resolved, str(entry["repo_id"]))
    import wave

    with wave.open(str(wav), "rb") as w:
        assert w.getnchannels() == 1 and w.getframerate() == 16_000 and w.getsampwidth() == 2, (
            "mono 16 kHz PCM16"
        )
        pcm = w.readframes(w.getnframes())
    stt = MlxWhisperStt(str(path), registry_id="whisper-large-v3-turbo")
    t0 = time.perf_counter()
    res = await stt.transcribe(pcm, language=None)
    print(
        json.dumps(
            {
                "text": res.text,
                "language": res.language,
                "stt_ms": res.latency_ms,
                "wall_ms": int((time.perf_counter() - t0) * 1000),
            },
            indent=2,
        )
    )


async def run_tts(text: str, out: Path) -> None:
    s = get_settings()
    tts = KokoroClient(s.kokoro_url)
    pcm = bytearray()
    first = None
    t0 = time.perf_counter()
    async for chunk in tts.stream(text, voice="af_heart", lang=None):
        if first is None:
            first = int((time.perf_counter() - t0) * 1000)
        pcm += chunk.pcm16
        rate = chunk.sample_rate
    out.write_bytes(wav_bytes(bytes(pcm), rate))  # noqa: ASYNC240
    print(
        json.dumps(
            {"first_audio_ms": first, "seconds": len(pcm) / 2 / rate, "wrote": str(out)}, indent=2
        )
    )


def record(seconds: float, keep: bool) -> Path:
    import sounddevice as sd  # type: ignore[import-not-found]

    print(f"recording {seconds:.0f} s from the default microphone…", file=sys.stderr)
    data = sd.rec(int(seconds * 16_000), samplerate=16_000, channels=1, dtype="int16")
    sd.wait()
    target = (
        Path(__file__).with_name("spike_mic.wav")
        if keep
        else Path(tempfile.mkdtemp(prefix="audhs-spike-")) / "mic.wav"
    )
    target.write_bytes(wav_bytes(data.tobytes()))
    return target


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--stt", type=Path)
    ap.add_argument("--tts")
    ap.add_argument("--mic", type=float)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    r = readiness()
    print(json.dumps(r, indent=2))
    if args.stt or args.mic:
        if not (r["stt_snapshot"] and r["stt_package"]):
            print("STT not ready — gate pending (see fixes above)", file=sys.stderr)
            return 2
    if args.tts and not r["tts_server"]:
        print("TTS not ready — gate pending (see fixes above)", file=sys.stderr)
        return 2
    if args.mic:
        if not r["sounddevice"]:
            print("--mic needs the optional `sounddevice` package", file=sys.stderr)
            return 2
        wav = record(args.mic, args.keep)
        try:
            asyncio.run(run_stt(wav))
        finally:
            if not args.keep:
                wav.unlink(missing_ok=True)
                wav.parent.rmdir()
    if args.stt:
        asyncio.run(run_stt(args.stt))
    if args.tts:
        out = (
            Path(__file__).with_name("spike_tts.wav")
            if args.keep
            else Path(tempfile.mkdtemp(prefix="audhs-spike-")) / "spike_tts.wav"
        )
        asyncio.run(run_tts(args.tts, out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
