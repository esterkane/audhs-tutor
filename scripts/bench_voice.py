#!/usr/bin/env python3
"""Voice benchmark (P9 / roadmap Stage 5): 20 turns through the real STT → LLM → TTS pipeline,
measuring STT, LLM first token, TTS first audio and total (utterance end → first audible sample),
median and p95, failures, model versions and hardware. Refuses to run unless the approved local
resources are installed and reachable (no synthetic timings are ever reported as a pass).

  bench_voice.py --wavs DIR    mono 16 kHz WAV utterances (≥ 20; reused cyclically) — your own
                               recordings; nothing is bundled
  [--transcripts FILE]         reference text per utterance (`<wav stem> <TEXT>` per line, the
                               LibriSpeech `*.trans.txt` layout) → word error rate per turn
  [--dataset LABEL] [--own-recordings]   what the audio is; the Stage-5 gate (ADR-0011) needs
                               ≥ 20 of the owner's own recordings — a public corpus is measured
                               and reported, but never marked as that gate
  [--turns 20] [--out evals/results/bench_voice.json]

The roadmap target is median ≤ 2 s to first audio. This script measures from the end of the
utterance on the server; the microphone-to-server hop is added by the browser and is reported
separately by the session screen's latency line.
"""

import argparse
import asyncio
import json
import platform
import re
import statistics
import sys
import time
import wave
from pathlib import Path
from typing import Any

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


_WORD = re.compile(r"[^a-z0-9' ]+")
_SENTENCE = re.compile(r"[.!?](\s|$)")


def normalise(text: str) -> list[str]:
    return _WORD.sub(" ", text.lower().replace("-", " ")).split()


def word_error_rate(reference: str, hypothesis: str) -> float | None:
    """Levenshtein distance over normalised words / reference length; None without a reference."""
    ref, hyp = normalise(reference), normalise(hypothesis)
    if not ref:
        return None
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return round(prev[-1] / len(ref), 4)


def load_transcripts(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stem, _, text = line.strip().partition(" ")
        if stem and text:
            out[stem] = text
    return out


async def bench(
    wavs: list[Path],
    turns: int,
    *,
    transcripts: dict[str, str] | None = None,
    dataset: str = "own recordings",
    own_recordings: bool = True,
    first_clause_mode: bool = False,
) -> dict[str, object]:
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
    rows: list[dict[str, Any]] = []
    failures = 0
    async with factory() as db:
        # a disposable DB (DATABASE_URL) has no registry rows yet: seed them from the profiles,
        # marking the Ollama tags that are actually installed as ready — never pulls anything
        from app.models_ai import registry
        from app.models_ai.factory import installed_models

        await registry.seed_defaults(db, installed_ollama_tags=await installed_models(s))
        await db.commit()
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
                reference = (transcripts or {}).get(wav.stem)
                wer = word_error_rate(reference, res.text) if reference else None
                from app.models_ai.gateway import StreamHandle
                from app.voice.loop import first_clause, speakable, speech_chunks

                h = StreamHandle()
                text = ""
                t_first_tok: float | None = None
                t_clause: float | None = None
                clause_text = ""
                t_sentence: float | None = None
                sentence_text = ""
                sentence_tts: asyncio.Task[float | None] | None = None

                async def first_audio_at(utterance: str) -> float | None:
                    async for _chunk in tts.stream(utterance, voice="af_heart", lang=None):
                        return time.perf_counter()
                    return None

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
                    if t_first_tok is None:
                        t_first_tok = time.perf_counter()
                    text += tok
                    if t_clause is None:
                        fc = first_clause(text)
                        if fc is not None:
                            t_clause, clause_text = time.perf_counter(), speakable(fc[0])
                    if t_sentence is None:
                        # exactly the loop's decision (voice/loop.py speech_chunks): the first
                        # sentence, or with --first-clause the first closed clause of it
                        ready, _rest = speech_chunks(text, first=True, early=first_clause_mode)
                        if ready and len(ready[0].split()) >= 3:
                            t_sentence, sentence_text = time.perf_counter(), speakable(ready[0])
                            sentence_tts = asyncio.create_task(first_audio_at(sentence_text))
                t_llm_done = time.perf_counter()
                if sentence_tts is None:  # no sentence boundary at all: speak everything
                    t_sentence, sentence_text = t_llm_done, speakable(text) or "Say hello."
                    sentence_tts = asyncio.create_task(first_audio_at(sentence_text))
                t_audio = await sentence_tts
                assert t_sentence is not None
                # pure synthesis time of the first clause, measured on its own afterwards, gives a
                # projection for starting TTS at the first clause instead of the first sentence
                clause_tts_ms: int | None = None
                first_audio_clause_est: int | None = None
                if t_clause is not None and clause_text and clause_text != sentence_text:
                    tc0 = time.perf_counter()
                    tc1 = await first_audio_at(clause_text)
                    if tc1 is not None:
                        clause_tts_ms = int((tc1 - tc0) * 1000)
                        first_audio_clause_est = int((t_clause - t0) * 1000) + clause_tts_ms
                t_llm_first = t_first_tok or t_llm_done
                rows.append(
                    {
                        "turn": i + 1,
                        "wav": wav.name,
                        "stt_ms": int((t_stt - t0) * 1000),
                        "llm_first_token_ms": int((t_llm_first - t_stt) * 1000),
                        "llm_generation_ms": int((t_llm_done - t_llm_first) * 1000),
                        "first_sentence_ready_ms": int((t_sentence - t0) * 1000),
                        "tts_sentence_ms": (
                            int((t_audio - t_sentence) * 1000) if t_audio is not None else None
                        ),
                        "total_ms": int(((t_audio or time.perf_counter()) - t0) * 1000),
                        "first_clause_ready_ms": (
                            int((t_clause - t0) * 1000) if t_clause is not None else None
                        ),
                        "tts_clause_ms": clause_tts_ms,
                        "first_audio_clause_est_ms": first_audio_clause_est,
                        "sentence_words": len(sentence_text.split()),
                        "clause_words": len(clause_text.split()) if clause_text else None,
                        "reply_chars": len(text),
                        "transcript_chars": len(res.text),
                        "transcript": res.text[:200],
                        "wer": wer,
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
    wers = [float(r["wer"]) for r in rows if r.get("wer") is not None]
    median_ok = bool(totals) and failures == 0 and statistics.median(totals) <= 2000

    def med(key: str) -> float | None:
        vals = [float(r[key]) for r in rows if r.get(key) is not None]
        return statistics.median(vals) if vals else None

    def p95(key: str) -> float | None:
        vals = sorted(float(r[key]) for r in rows if r.get(key) is not None)
        return vals[max(0, int(len(vals) * 0.95) - 1)] if vals else None

    return {
        "mode": "first_clause" if first_clause_mode else "sentence",
        "dataset": dataset,
        "own_recordings": own_recordings,
        "stage5_gate": (
            "measured on the owner's own recordings"
            if own_recordings
            else "NOT the Stage-5 gate: public corpus, not the owner's voice (ADR-0011)"
        ),
        "turns": turns,
        "failures": failures,
        "wer_median": statistics.median(wers) if wers else None,
        "wer_mean": round(sum(wers) / len(wers), 4) if wers else None,
        "wer_turns": len(wers),
        "median_total_ms": statistics.median(totals) if totals else None,
        "p95_total_ms": p95("total_ms"),
        "stages_median_ms": {
            "stt": med("stt_ms"),
            "llm_first_token": med("llm_first_token_ms"),
            "llm_generation": med("llm_generation_ms"),
            "first_sentence_ready": med("first_sentence_ready_ms"),
            "tts_sentence": med("tts_sentence_ms"),
            "first_clause_ready": med("first_clause_ready_ms"),
            "tts_clause": med("tts_clause_ms"),
        },
        "first_audio_clause_est_median_ms": med("first_audio_clause_est_ms"),
        "measurement": (
            "total_ms = utterance end → first audio, with TTS started at the first "
            + ("closed clause" if first_clause_mode else "sentence boundary")
            + " while the LLM streams (voice/loop.py speech_chunks, voice.early_speech "
            + ("on" if first_clause_mode else "off")
            + "); tts_sentence_ms is the synthesis time of that first chunk alone"
            + (
                ""
                if first_clause_mode
                else "; first_audio_clause_est_ms = first clause boundary + its own synthesis "
                "time measured afterwards (a projection — run --first-clause for the real number)"
            )
        ),
        "target_median_ms": 2000,
        "latency_target_met": median_ok,
        "passed": median_ok and own_recordings,
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
    ap.add_argument("--transcripts", type=Path, help="reference text per wav stem (WER)")
    ap.add_argument(
        "--first-clause",
        action="store_true",
        help="start TTS at the first closed clause (the loop's voice.early_speech behaviour)",
    )
    ap.add_argument("--dataset", default="own recordings", help="label for the report")
    ap.add_argument(
        "--own-recordings",
        action="store_true",
        help="the audio is the owner's own voice (required for the Stage-5 gate)",
    )
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
    if len(wavs) < 20:
        print(f"only {len(wavs)} WAV files; the benchmark wants ≥ 20 utterances", file=sys.stderr)
        return 2
    report = asyncio.run(
        bench(
            wavs,
            args.turns,
            transcripts=load_transcripts(args.transcripts),
            dataset=args.dataset,
            own_recordings=args.own_recordings,
            first_clause_mode=args.first_clause,
        )
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    if not args.own_recordings:
        print(
            "note: measured on a public corpus — the Stage-5 gate needs the owner's own "
            "recordings (--own-recordings); this run is evidence, not the gate",
            file=sys.stderr,
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
