#!/usr/bin/env python3
"""Retrieval evals: recall@k, MRR, citation coverage, latency over evals/retrieval/queries.yaml.
usage: eval_retrieval.py [--k 8] [--queries PATH] [--out evals/results/retrieval_latest.json]
                         [--baseline evals/results/retrieval_baseline.json] [--min-recall 0.8]
                         [--db data/dev.db] [--embedding-version 1]
Runs against the SQLite database and Qdrant collection you point it at (default: the dev corpus).
Exit 1 when recall@k is below --min-recall or regresses by more than 0.05 against the baseline."""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.evals.retrieval import compare, evaluate, load_queries  # noqa: E402
from app.knowledge.reindex import build_repo  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--queries", type=Path, default=ROOT / "evals" / "retrieval" / "queries.yaml")
    ap.add_argument(
        "--out", type=Path, default=ROOT / "evals" / "results" / "retrieval_latest.json"
    )
    ap.add_argument(
        "--baseline", type=Path, default=ROOT / "evals" / "results" / "retrieval_baseline.json"
    )
    ap.add_argument("--min-recall", type=float, default=0.8)
    ap.add_argument("--db", type=Path, default=None, help="SQLite file (default: DATABASE_URL)")
    ap.add_argument("--embedding-version", type=int, default=1)
    args = ap.parse_args()

    s = get_settings()
    if args.db:
        s = s.model_copy(update={"database_url": f"sqlite+aiosqlite:///{args.db.resolve()}"})
    engine = make_engine(s.database_url_resolved)
    repo = None
    try:
        async with make_session_factory(engine)() as db:
            repo = await build_repo(db, s, embedding_version=args.embedding_version)
        queries = load_queries(args.queries)
        report = await evaluate(repo, queries, k=args.k)
    finally:
        if repo is not None:
            await repo.client.close()
        await engine.dispose()

    baseline = json.loads(args.baseline.read_text()) if args.baseline.exists() else None
    deltas = compare(report, baseline)
    payload = {
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        **report.model_dump(),
        "deltas": deltas,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))

    print(
        f"recall@{report.k} {report.recall_at_k:.3f} (@4 {report.recall_at_4:.3f}, @1 {report.recall_at_1:.3f}) "
        f"· MRR {report.mrr:.3f} · citation coverage "
        f"{report.citation_coverage:.3f} · latency p50 {report.latency_p50_ms} ms / p95 {report.latency_p95_ms} ms "
        f"· {report.queries} queries on {report.collection}"
    )
    for r in report.results:
        if r.recall < 1.0:
            print(f"  MISS {r.id}: {r.query!r} → {r.hits[:3]}")
    if deltas:
        print("vs baseline: " + ", ".join(f"{k} {v:+.3f}" for k, v in deltas.items()))
    print(f"written {args.out}")
    if report.recall_at_k < args.min_recall:
        print(f"FAIL recall@{report.k} {report.recall_at_k:.3f} < {args.min_recall}")
        return 1
    if deltas.get("recall_at_k", 0.0) < -0.05:
        print("FAIL recall regressed by more than 0.05 against the baseline")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
