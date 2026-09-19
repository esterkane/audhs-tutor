"""Model benchmark (ADR-0010): speed + 5-case hard-check tutoring eval -> benchmark_json."""

import re
import time
from datetime import UTC, datetime
from typing import Any

from app.core.config import PROJECT_ROOT
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import Message, ModelProvider, ModelSpec

PEDAGOGY_PROMPT = PROJECT_ROOT / "prompts" / "_base" / "pedagogy.v1.md"

TUTOR_CASES: list[dict[str, str]] = [
    {
        "id": "hint-gd",
        "learner": "Why does gradient descent overshoot with a large learning rate? "
        "Give me a hint, not the answer.",
    },
    {"id": "hint-softmax", "learner": "I don't get why attention uses softmax. One hint please."},
    {
        "id": "check-kv",
        "learner": "Explain the KV cache briefly and then check whether I understood.",
    },
    {
        "id": "error-shape",
        "learner": "My matmul fails with shapes (3,4) and (3,4). What went wrong? Don't just fix it.",
    },
    {"id": "options", "learner": "I'm stuck choosing how to review transformers today."},
]

BANNED = [
    r"great question",
    r"learning style",
    r"visual learner",
    r"how do you feel",
    r"don't worry",
    r"streak",
    r"awesome job",
]
SPEED_PROMPT = (
    "Write a plain, factual paragraph of about 150 words explaining what a hash map is, "
    "how collisions are handled, and when to prefer a tree map instead."
)


def sentences(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def hard_checks(text: str) -> dict[str, bool]:
    low = text.lower()
    return {
        "brevity_le_6_sentences": sentences(text) <= 6,
        "no_banned_language": not any(re.search(p, low) for p in BANNED),
        "asks_or_offers_next_step": "?" in text or bool(re.search(r"\b(option|try|next)\b", low)),
    }


def load_policy() -> str:
    if PEDAGOGY_PROMPT.exists():
        return PEDAGOGY_PROMPT.read_text()
    return "You are a tutor. Hint first, brief, literal. Ask a check question."


async def bench_model(
    provider: ModelProvider,
    spec: ModelSpec,
    *,
    cases: list[dict[str, str]] | None = None,
    max_tokens: int = 180,
) -> dict[str, Any]:
    """Speed (tok/s, first-token ms) + tutoring hard checks. Cheap enough to run after every pull."""
    out: dict[str, Any] = {"benchmarked_at": datetime.now(UTC).isoformat(timespec="seconds")}
    # --- speed
    t0 = time.perf_counter()
    first: float | None = None
    n_chunks = 0
    async for _ in provider.stream(
        spec, [Message(role="user", content=SPEED_PROMPT)], max_tokens=200
    ):
        if first is None:
            first = time.perf_counter()
        n_chunks += 1
    end = time.perf_counter()
    out["first_token_ms"] = int(((first or end) - t0) * 1000)
    out["stream_chunks"] = n_chunks
    if isinstance(provider, OllamaProvider):
        stats = await provider.generate_stats(spec, SPEED_PROMPT, max_tokens=200)
        out["tok_per_s"] = round(stats["tok_per_s"], 1)
        out["prompt_eval_ms"] = int(stats["prompt_eval_ms"])
    else:
        gen_s = max(end - (first or t0), 1e-6)
        out["tok_per_s"] = round(n_chunks / gen_s, 1)  # chunk-rate approximation for hosted
    # --- tutoring hard checks
    policy = load_policy()
    results = []
    passed = total = 0
    latencies = []
    for case in cases or TUTOR_CASES:
        msgs = [
            Message(role="system", content=policy),
            Message(role="user", content=case["learner"]),
        ]
        r = await provider.complete(spec, msgs, max_tokens=max_tokens)
        checks = hard_checks(r.text)
        passed += sum(checks.values())
        total += len(checks)
        latencies.append(r.latency_ms)
        results.append({"id": case["id"], "checks": checks, "sentences": sentences(r.text)})
    out["tutoring_hard_checks"] = {
        "passed": passed,
        "total": total,
        "score": round(passed / total, 3) if total else 0.0,
        "cases": results,
    }
    out["latency_ms_median"] = sorted(latencies)[len(latencies) // 2] if latencies else None
    return out


def summarize(bench: dict[str, Any] | None) -> str:
    if not bench:
        return "-"
    hc = bench.get("tutoring_hard_checks", {})
    return (
        f"{bench.get('tok_per_s', '?')} tok/s, ftl {bench.get('first_token_ms', '?')} ms, "
        f"eval {hc.get('passed', '?')}/{hc.get('total', '?')}"
    )
