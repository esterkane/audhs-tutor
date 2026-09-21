#!/usr/bin/env python3
"""Voice benchmark (P9 / roadmap Stage 5): 20 turns through the real STT → LLM → TTS pipeline,
measuring STT, LLM first token, TTS first audio and total (utterance end → first audible sample),
median and p95, failures, model versions and hardware. Refuses to run unless the approved local
resources are installed and reachable (no synthetic timings are ever reported as a pass).

  bench_voice.py --wavs DIR    mono 16 kHz WAV utterances (≥ 20; reused cyclically) — your own
                               recordings; nothing is bundled
  [--turns 20] [--out evals/results/bench_voice.json]

The roadmap target is median ≤ 2 s to first audio. This script measures from the end of the
utterance on the server; the microphone-to-server hop is added by the browser and is reported
separately by the session screen's latency line.
"""

import argparse
import asyncio
import json
import platform
import statistics
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.models_ai.factory import mlx_cached  # noqa: E402
from app.models_ai.routing import load_profiles  # noqa: E402
from app.voice.tts import KokoroClient, kokoro_reachable  # noqa: E402


def gate() -> list[str]:
    s = get_settings()
    problems = []
    entry = next(
        e for e in load_profiles()["registry_defaults"] if e["id"] == "whisper-large-v3-turbo"
    )
    if not mlx_cached(s.models_dir_resolved, str(entry["repo_id"])):
        problems.append("whisper-large-v3-turbo snapshot not pulled")
    import importlib.util

    if importlib.util.find_spec("mlx_whisper") is None:
        problems.append("mlx-whisper package not installed (uv sync --group stt)")
    if not asyncio.run(kokoro_reachable(s.kokoro_url)):
        problems.append(f"Kokoro server not reachable at {s.kokoro_url}")
    return problems


async def bench(wavs: list[Path], turns: int) -> dict[str, object]:
    from app.core.config import get_settings
    from app.db.session import make_engine, make_session_factory
    from app.kernel.learner import get_or_create_owner
    from app.models_ai.budget import Budget
    from app.models_ai.factory import build_providers, mlx_snapshot_dir
    from app.models_ai.gateway import ModelGateway
    from app.models_ai.provider import Message, TaskClass
    from app.models_ai.routing import Router
    from app.voice.stt import MlxWhisperStt

    s = get_settings()
    engine = make_engine(s.database_url_resolved)
    factory = make_session_factory(engine)
    entry = next(
        e for e in load_profiles()["registry_defaults"] if e["id"] == "whisper-large-v3-turbo"
    )
    stt = MlxWhisperStt(
        str(mlx_snapshot_dir(s.models_dir_resolved, str(entry["repo_id"]))),
        registry_id="whisper-large-v3-turbo",
    )
    tts = KokoroClient(s.kokoro_url)
    rows = []
    failures = 0
    async with factory() as db:
        owner = await get_or_create_owner(db)
        gw = ModelGateway(
            db, Router(s.routing_profile), build_providers(s), Budget(s.daily_budget_usd)
        )
        for i in range(turns):
            wav = wavs[i % len(wavs)]
            with wave.open(str(wav), "rb") as w:
                pcm = w.readframes(w.getnframes())
            t0 = time.perf_counter()
            try:
                res = await stt.transcribe(pcm, language=None)
                t_stt = time.perf_counter()
                first_tok = None
                text = ""
                from app.models_ai.gateway import StreamHandle

                h = StreamHandle()
                async for tok in gw.stream(
                    TaskClass.CHAT,
                    [
                        Message(role="system", content="Answer in two short spoken sentences."),
                        Message(role="user", content=res.text or "Say hello."),
                    ],
                    handle=h,
                    learner_id=owner.id,
                    max_tokens=80,
                ):
                    if first_tok is None:
                        first_tok = time.perf_counter()
                    text += tok
                t_llm_first = first_tok or time.perf_counter()
                first_audio = None
                async for _chunk in tts.stream(
                    text.split(".")[0] or text, voice="af_heart", lang=None
                ):
                    first_audio = time.perf_counter()
                    break
                t_audio = first_audio or time.perf_counter()
                rows.append(
                    {
                        "turn": i + 1,
                        "wav": wav.name,
                        "stt_ms": int((t_stt - t0) * 1000),
                        "llm_first_token_ms": int((t_llm_first - t_stt) * 1000),
                        "tts_first_audio_ms": int((t_audio - t_llm_first) * 1000),
                        "total_ms": int((t_audio - t0) * 1000),
                        "transcript_chars": len(res.text),
                        "model": h.registry_id,
                    }
                )
            except Exception as e:  # noqa: BLE001
                failures += 1
                rows.append(
                    {"turn": i + 1, "wav": wav.name, "error": f"{type(e).__name__}: {e}"[:200]}
                )
    await engine.dispose()
    totals = [r["total_ms"] for r in rows if "total_ms" in r]
    return {
        "turns": turns,
        "failures": failures,
        "median_total_ms": statistics.median(totals) if totals else None,
        "p95_total_ms": (sorted(totals)[max(0, int(len(totals) * 0.95) - 1)] if totals else None),
        "target_median_ms": 2000,
        "passed": bool(totals) and failures == 0 and statistics.median(totals) <= 2000,
        "hardware": {
            "machine": platform.machine(),
            "system": platform.platform(),
            "python": platform.python_version(),
        },
        "models": {
            "stt": "whisper-large-v3-turbo (mlx-community)",
            "tts": "kokoro-82m via KOKORO_URL",
            "llm": rows[0].get("model") if rows else None,
        },
        "rows": rows,
        "note": "server-side: utterance end → first audio sample; browser mic/playback hops not included",
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--wavs", type=Path, required=True)
    ap.add_argument("--turns", type=int, default=20)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "evals" / "results" / "bench_voice.json",
    )
    args = ap.parse_args()
    problems = gate()
    if problems:
        print("voice benchmark gate PENDING — not run:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 2
    wavs = sorted(p for p in args.wavs.glob("*.wav"))
    if not wavs:
        print("no WAV files in", args.wavs, file=sys.stderr)
        return 2
    report = asyncio.run(bench(wavs, args.turns))
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
