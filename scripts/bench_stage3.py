#!/usr/bin/env python3
"""Stage 3 benchmark (docs/ROADMAP.md). Run: make bench s=3
A ≥ 5 courses ingested (seeds/courses, mixed VTT/SRT/ipynb/md/txt + seeds/untrusted at trust 0) into an
  isolated SQLite (data/bench3.db) and a throwaway Qdrant collection; second run is a no-op (idempotent)
B recall@8 ≥ 0.8 on the labelled set (evals/retrieval/queries.yaml) with the real embedder + BM25
C poisoned-chunk tests pass (pytest tests/test_untrusted_guard.py + the data-block test)
D p95 hybrid search latency < 300 ms at the current corpus size (labelled queries × 3 rounds)
E Qdrant RAM < 1 GB (memory_active_bytes from /metrics, plus docker stats when available)
"""

import asyncio
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import PROJECT_ROOT, get_settings  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.evals.harness import results_dir  # noqa: E402
from app.evals.retrieval import evaluate, load_queries  # noqa: E402
from app.knowledge.ingest.service import ingest_path  # noqa: E402
from app.knowledge.reindex import build_repo  # noqa: E402
from app.models_ai import registry  # noqa: E402
from app.models_ai.factory import installed_models  # noqa: E402

EMBEDDING_VERSION = 903  # throwaway collection corpus_v903
results: dict[str, dict[str, Any]] = {}


def record(key: str, status: str, **data: Any) -> None:
    results[key] = {"status": status, **data}
    print(f"[{status:4}] {key}: {json.dumps(data, default=str)[:700]}", flush=True)


async def check_a(db: Any, repo: Any) -> None:
    t0 = time.perf_counter()
    courses = await ingest_path(db, ROOT / "seeds" / "courses", trust_tier=2, repo=repo)
    forum = await ingest_path(
        db, ROOT / "seeds" / "untrusted", course="Forum dump", trust_tier=0, repo=repo
    )
    elapsed = round(time.perf_counter() - t0, 1)
    s = courses.summary()
    again = (await ingest_path(db, ROOT / "seeds" / "courses", trust_tier=2, repo=repo)).summary()
    indexed = await repo.count()
    ok = (
        len(s["courses"]) >= 5
        and s["skipped"] == 0
        and again["new_versions"] == 0
        and again["indexed"] == 0
        and indexed == s["chunks"] + forum.summary()["chunks"]
        and forum.summary()["flagged"] == 1
    )
    record(
        "A ≥5 courses ingested, idempotent, indexed",
        "PASS" if ok else "FAIL",
        courses=s["courses"],
        documents=s["documents"],
        chunks=s["chunks"],
        deduped=s["deduped"],
        flagged_course=s["flagged"],
        flagged_forum=forum.summary()["flagged"],
        skipped=courses.skipped,
        rerun=again,
        index_count=indexed,
        seconds=elapsed,
        source_types=sorted({r.source_type for r in courses.results}),
    )


async def check_b(repo: Any) -> Any:
    queries = load_queries(ROOT / "evals" / "retrieval" / "queries.yaml")
    report = await evaluate(repo, queries, k=8)
    record(
        "B recall@8 ≥ 0.8 on labelled queries",
        "PASS" if report.recall_at_k >= 0.8 else "FAIL",
        recall_at_8=report.recall_at_k,
        recall_at_4=report.recall_at_4,
        recall_at_1=report.recall_at_1,
        mrr=report.mrr,
        citation_coverage=report.citation_coverage,
        queries=report.queries,
        misses=report.misses,
        collection=report.collection,
    )
    return report


def check_c() -> None:
    proc = subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "tests/test_untrusted_guard.py",
            "tests/test_orchestrator.py::test_data_block_escapes_and_flags_poison",
        ],
        cwd=ROOT / "backend",
        capture_output=True,
        text=True,
    )
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-300:]
    record(
        "C poisoned-chunk tests pass",
        "PASS" if proc.returncode == 0 else "FAIL",
        result=tail,
    )


async def check_d(repo: Any) -> None:
    queries = load_queries(ROOT / "evals" / "retrieval" / "queries.yaml")
    await repo.search("warm up", k=8)
    latencies: list[int] = []
    for _ in range(3):
        for q in queries:
            t0 = time.perf_counter()
            await repo.search(q.query, k=8)
            latencies.append(int((time.perf_counter() - t0) * 1000))
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[min(len(latencies) - 1, round((len(latencies) - 1) * 0.95))]
    record(
        "D p95 search < 300 ms",
        "PASS" if p95 < 300 else "FAIL",
        p50_ms=p50,
        p95_ms=p95,
        max_ms=latencies[-1],
        searches=len(latencies),
        corpus_chunks=await repo.count(),
        reranker=getattr(getattr(repo, "reranker", None), "model", None),
    )


def check_e(qdrant_url: str) -> None:
    active = allocated = None
    try:
        text = httpx.get(f"{qdrant_url}/metrics", timeout=3.0).text
        m = re.search(r"^memory_active_bytes (\d+)", text, re.M)
        active = int(m.group(1)) if m else None
        m = re.search(r"^memory_allocated_bytes (\d+)", text, re.M)
        allocated = int(m.group(1)) if m else None
    except httpx.HTTPError:
        pass
    docker_mem = None
    try:
        out = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}} {{.MemUsage}}"],
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout
        for line in out.splitlines():
            if "qdrant" in line:
                docker_mem = line.split(" ", 1)[1]
    except (OSError, subprocess.SubprocessError):
        pass
    if active is None:
        record("E Qdrant RAM < 1 GB", "SKIP", reason="Qdrant /metrics unreachable")
        return
    gb = active / 1e9
    record(
        "E Qdrant RAM < 1 GB",
        "PASS" if gb < 1.0 else "FAIL",
        memory_active_gb=round(gb, 3),
        memory_allocated_gb=round((allocated or 0) / 1e9, 3),
        docker_stats=docker_mem,
    )


async def main() -> int:
    s = get_settings()
    db_path = PROJECT_ROOT / "data" / "bench3.db"
    if db_path.exists():
        db_path.unlink()
    settings = s.model_copy(
        update={"database_url": f"sqlite+aiosqlite:///{db_path}", "auto_migrate": False}
    )
    upgrade_to_head(settings.sync_database_url)
    engine = make_engine(settings.database_url_resolved)
    repo = None
    try:
        async with make_session_factory(engine)() as db:
            await registry.seed_defaults(db, installed_ollama_tags=await installed_models(settings))
            repo = await build_repo(db, settings, embedding_version=EMBEDDING_VERSION)
            await repo.ensure_collection(recreate=True)
            for name, fn in (("A", lambda: check_a(db, repo)), ("B", lambda: check_b(repo))):
                try:
                    await fn()
                except Exception as e:
                    record(f"{name} (crashed)", "FAIL", error=f"{type(e).__name__}: {e}")
            check_c()
            try:
                await check_d(repo)
            except Exception as e:
                record("D (crashed)", "FAIL", error=f"{type(e).__name__}: {e}")
            check_e(settings.qdrant_url)
    finally:
        if repo is not None:
            try:
                await repo.client.delete_collection(repo.collection)
            finally:
                await repo.client.close()
        await engine.dispose()
    out = results_dir() / "bench_stage3.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    failed = [k for k, v in results.items() if v["status"] == "FAIL"]
    print(
        "\nSTAGE 3 BENCHMARK:",
        "FAIL" if failed else "PASS",
        f"({len(results)} checks, {len(failed)} failed)",
    )
    print(f"written: {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
