#!/usr/bin/env python3
"""Stage 0 benchmark (docs/ROADMAP.md). Run: make bench s=0

Checks
  A  local `chat` >= 15 tok/s
  B  one `grade_rubric` call routes to Claude and lands in model_call with cost  (SKIP without API key)
  C  budget cap trips at the configured amount (isolated tmp DB, fake providers)
  D  a model downloaded from Hugging Face via scripts/models.py pull is benchmarked and assigned to chat
  E  1k-chunk sample round-trips through Qdrant with a payload-filtered hybrid query
Prints a PASS/FAIL/SKIP table + JSON; exit 1 on any FAIL.
"""

import asyncio
import json
import random
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from qdrant_client import AsyncQdrantClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.db import models  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.knowledge.provenance import Provenance  # noqa: E402
from app.knowledge.qdrant_hybrid import QdrantHybridRepository  # noqa: E402
from app.knowledge.repository import ChunkRecord, SearchFilters  # noqa: E402
from app.models_ai import registry  # noqa: E402
from app.models_ai.budget import Budget  # noqa: E402
from app.models_ai.downloader import hf_info  # noqa: E402
from app.models_ai.factory import build_gateway  # noqa: E402
from app.models_ai.fake import FakeProvider  # noqa: E402
from app.models_ai.gateway import ModelGateway  # noqa: E402
from app.models_ai.ollama import OllamaProvider  # noqa: E402
from app.models_ai.provider import Message, TaskClass  # noqa: E402
from app.models_ai.routing import Router  # noqa: E402

HF_REPO = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
HF_FILE_HINT = "q4_k_m"
HF_ID = "qwen25-05b-q4"

results: dict[str, dict[str, Any]] = {}


def record(key: str, status: str, **data: Any) -> None:
    results[key] = {"status": status, **data}
    print(f"[{status:4}] {key}: {json.dumps(data, default=str)}", flush=True)


def models_cli(*args: str) -> tuple[int, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / "models.py"), *args]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT / "backend")
    return p.returncode, (p.stdout + p.stderr)[-1500:]


# ----------------------------------------------------------------------------- A
async def check_a_speed(db: AsyncSession, s: Settings) -> None:
    route = await Router(s.routing_profile).resolve(db, TaskClass.CHAT)
    spec = await registry.get_spec(db, route.registry_id)
    prov = OllamaProvider(s.ollama_host)
    stats = await prov.generate_stats(
        spec, "Explain in about 150 words how a hash map handles collisions.", max_tokens=200
    )
    tps = round(stats["tok_per_s"], 1)
    record(
        "A local chat tok/s >= 15",
        "PASS" if tps >= 15 else "FAIL",
        model=spec.registry_id,
        tok_per_s=tps,
    )


# ----------------------------------------------------------------------------- B
async def check_b_hosted(db: AsyncSession, s: Settings) -> None:
    if not s.anthropic_api_key:
        record(
            "B grade_rubric -> Claude with cost", "SKIP", reason="ANTHROPIC_API_KEY empty in .env"
        )
        return
    gw = build_gateway(db, s)
    before = (await db.execute(select(models.ModelCall))).scalars().all()
    out = await gw.complete(
        TaskClass.GRADE_RUBRIC,
        [
            Message(
                role="system",
                content="You grade one-sentence answers. Reply in one short sentence.",
            ),
            Message(
                role="user",
                content="Criterion: mentions sqrt(d_k). Answer: 'we divide by root of d_k'. Pass?",
            ),
        ],
        max_tokens=60,
    )
    row = await db.get(models.ModelCall, out.model_call_id)
    ok = (
        row is not None
        and row.provider == "anthropic"
        and row.cost_usd > 0
        and row.task == "grade_rubric"
    )
    record(
        "B grade_rubric -> Claude with cost",
        "PASS" if ok else "FAIL",
        registry_id=out.registry_id,
        model=row.model if row else None,
        cost_usd=row.cost_usd if row else None,
        tokens=(row.tokens_in, row.tokens_out) if row else None,
        model_call_rows_added=len((await db.execute(select(models.ModelCall))).scalars().all())
        - len(before),
    )


# ----------------------------------------------------------------------------- C
async def check_c_budget() -> None:
    tmp = Path(tempfile.mkdtemp()) / "budget.db"
    engine = make_engine(f"sqlite+aiosqlite:///{tmp}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with make_session_factory(engine)() as db:
        await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "hosted"})
        cap = 0.25
        hosted = FakeProvider(text="hosted", tokens_in=100_000, tokens_out=0)  # $0.20/call at $2/M
        gw = ModelGateway(
            db,
            Router("default"),
            {"ollama": FakeProvider(text="local"), "anthropic": hosted},
            Budget(cap),
        )
        routes = []
        for _ in range(3):
            out = await gw.complete(TaskClass.TUTOR_DEEP, [Message(role="user", content="x")])
            routes.append((out.route, out.cost_usd))
        spent = await Budget(cap).spent_today(db)
    await engine.dispose()
    ok = routes[0][0] == "primary" and routes[-1][0] == "degraded" and spent >= cap
    record(
        "C budget cap trips",
        "PASS" if ok else "FAIL",
        cap_usd=cap,
        calls=routes,
        spent_usd=round(spent, 4),
    )


# ----------------------------------------------------------------------------- D
async def check_d_hf_pull(db: AsyncSession, s: Settings) -> None:
    default_chat = (await Router(s.routing_profile).resolve(db, TaskClass.CHAT)).registry_id
    steps: dict[str, Any] = {}
    # make sure the default chat model itself is benchmarked (needed to assign it back later)
    row = await registry.get_row(db, default_chat)
    if not row.benchmark_json:
        rc, out = models_cli("bench", default_chat)
        steps["bench_default"] = rc
        if rc != 0:
            record("D HF pull -> bench -> assign chat", "FAIL", step="bench default", out=out)
            return
    info = hf_info(HF_REPO, s.hf_token)
    files = [f["filename"] for f in info["gguf_files"] if HF_FILE_HINT in f["filename"].lower()]
    if not files:
        record(
            "D HF pull -> bench -> assign chat", "FAIL", step="pick file", files=info["gguf_files"]
        )
        return
    steps["file"] = files[0]
    steps["licence"] = info["licence"]
    for args in (
        (
            "add",
            "huggingface_gguf",
            HF_REPO,
            "--file",
            files[0],
            "--id",
            HF_ID,
            "--context-len",
            "8192",
        ),
        ("pull", HF_ID),
        ("bench", HF_ID),
        ("assign", "chat", HF_ID),
    ):
        t0 = time.perf_counter()
        rc, out = models_cli(*args)
        steps[args[0]] = {"rc": rc, "s": round(time.perf_counter() - t0, 1)}
        if rc != 0:
            record("D HF pull -> bench -> assign chat", "FAIL", step=args[0], out=out, **steps)
            return
    db.expire_all()
    row = await registry.get_row(db, HF_ID)
    pref = (
        await db.execute(
            select(models.LearnerPreference).where(models.LearnerPreference.key == "routing.chat")
        )
    ).scalar_one_or_none()
    route = await Router(s.routing_profile).resolve(
        db, TaskClass.CHAT, pref.learner_id if pref else None
    )
    ok = (
        row.status == "ready"
        and bool(row.benchmark_json)
        and pref is not None
        and route.registry_id == HF_ID
    )
    bench = row.benchmark_json or {}
    record(
        "D HF pull -> bench -> assign chat",
        "PASS" if ok else "FAIL",
        registry_id=HF_ID,
        row_status=row.status,
        size_gb=row.size_gb,
        tok_per_s=bench.get("tok_per_s"),
        first_token_ms=bench.get("first_token_ms"),
        hard_checks=bench.get("tutoring_hard_checks", {}).get("score"),
        routed_chat=route.registry_id,
        **steps,
    )
    # leave the system on the default chat model; the tiny model stays in the registry for experiments
    rc, out = models_cli("assign", "chat", default_chat)
    print(f"       restored routing.chat -> {default_chat} (rc={rc})")


# ----------------------------------------------------------------------------- E
TOPICS = [
    ("attention", "Scaled dot-product attention divides QK^T by sqrt(d_k) before the softmax"),
    ("multihead", "Multi-head attention projects queries keys and values into several subspaces"),
    ("kvcache", "The KV cache stores past keys and values so decoding avoids recomputation"),
    ("posenc", "Sinusoidal positional encodings inject token order into the embeddings"),
    ("layernorm", "Layer normalization rescales activations per token to stabilise training"),
    ("adam", "Adam combines momentum with per-parameter adaptive learning rates"),
    ("dropout", "Dropout randomly zeroes activations to regularise the network"),
    ("lora", "LoRA fine-tunes by learning low-rank update matrices for frozen weights"),
    ("tokenizer", "Byte-pair encoding merges frequent symbol pairs into subword tokens"),
    ("relu", "ReLU outputs max(0, x) and avoids saturating gradients for positive inputs"),
]
COURSES = ["Transformers 101", "Deep Learning Bootcamp", "LLM Engineering", "PyTorch Basics"]


def synth_chunks(n: int) -> list[ChunkRecord]:
    rnd = random.Random(7)
    out = []
    for i in range(n):
        key, base = TOPICS[i % len(TOPICS)]
        course = COURSES[i % len(COURSES)]
        kind = rnd.choice(["example", "derivation", "pitfall", "exercise"])
        text = f"{base}. Lecture note {i}: {kind} {rnd.randint(1, 99)}."
        out.append(
            ChunkRecord(
                id=f"bench-{i:04d}",
                text=text,
                skill_ids=[key],
                document_id=f"doc-{course}",
                ordinal=i,
                provenance=Provenance(
                    source_id=f"src-{course}",
                    path=f"{course}/sec{i % 5}/lec{i}.vtt",
                    source_type="udemy_caption",
                    trust_tier=2,
                    course=course,
                    section=str(i % 5),
                    lecture=str(i),
                    t_start=float(i % 600),
                ),
            )
        )
    return out


async def check_e_qdrant(db: AsyncSession, s: Settings) -> None:
    route = await Router(s.routing_profile).resolve(db, TaskClass.EMBED)
    spec = await registry.get_spec(db, route.registry_id)
    prov = OllamaProvider(s.ollama_host)
    dims = len((await prov.embed(spec, ["probe"]))[0])
    client = AsyncQdrantClient(url=s.qdrant_url)
    repo = QdrantHybridRepository(
        client, prov, spec, dims=dims, embedding_version=900, batch_size=64
    )
    try:
        chunks = synth_chunks(1000)
        t0 = time.perf_counter()
        n = await repo.reindex(chunks)
        index_s = round(time.perf_counter() - t0, 1)
        count = await repo.count()
        lat = []
        correct = 0
        for i in range(20):
            key, base = TOPICS[i % len(TOPICS)]
            course = COURSES[i % len(COURSES)]
            t1 = time.perf_counter()
            res = await repo.search(
                base.split(".")[0], filters=SearchFilters(course=course, skill_ids=[key]), k=8
            )
            lat.append((time.perf_counter() - t1) * 1000)
            hits = res.hits
            if hits and all(
                h.chunk.provenance.course == course and key in h.chunk.skill_ids for h in hits
            ):
                correct += 1
        p50, p95 = statistics.median(lat), sorted(lat)[int(0.95 * len(lat)) - 1]
        ok = n == 1000 and count == 1000 and correct == 20
        record(
            "E 1k chunks round-trip Qdrant + filtered hybrid query",
            "PASS" if ok else "FAIL",
            embed_model=spec.registry_id,
            dims=dims,
            indexed=n,
            count=count,
            index_s=index_s,
            filtered_queries_correct=f"{correct}/20",
            search_p50_ms=round(p50, 1),
            search_p95_ms=round(p95, 1),
            sparse_scores_present=bool(res.trace.bm25_scores),
            dense_scores_present=bool(res.trace.vector_scores),
        )
    finally:
        await client.delete_collection(repo.collection)
        await client.close()


async def main() -> int:
    s = get_settings()
    upgrade_to_head(s.sync_database_url)
    engine = make_engine(s.database_url_resolved)
    try:
        async with make_session_factory(engine)() as db:
            for name, fn in (
                ("A", check_a_speed),
                ("B", check_b_hosted),
                ("D", check_d_hf_pull),
                ("E", check_e_qdrant),
            ):
                try:
                    await fn(db, s)
                except Exception as e:  # keep going; report
                    record(f"{name} (crashed)", "FAIL", error=f"{type(e).__name__}: {e}")
            try:
                await check_c_budget()
            except Exception as e:
                record("C (crashed)", "FAIL", error=f"{type(e).__name__}: {e}")
    finally:
        await engine.dispose()
    out_dir = ROOT / "evals" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "bench_stage0.json").write_text(json.dumps(results, indent=2, default=str))
    failed = [k for k, v in results.items() if v["status"] == "FAIL"]
    print(
        "\nSTAGE 0 BENCHMARK:",
        "FAIL" if failed else "PASS",
        f"({len(results)} checks, {len(failed)} failed)",
    )
    print(f"written: {out_dir / 'bench_stage0.json'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
