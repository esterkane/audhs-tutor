#!/usr/bin/env python3
"""Ingest course material into SQLite and the retrieval index.

usage: ingest.py --src PATH [--course NAME] [--trust 0-3] [--type TYPE] [--no-index] [--json]

PATH is a file or a folder laid out like a Udemy export: <src>/<Course>/<NN - Section>/<NNN - Lecture>.ext
(.vtt .srt .ipynb .pdf .md .txt). With --course, <src> itself is the course folder.
Idempotent: unchanged files are no-ops; changed files get a new version. Trust is decided here,
never read from the files (ADR-0008). Default trust 2 = purchased course material.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.knowledge.ingest.service import ingest_path, rescan_flags  # noqa: E402
from app.knowledge.reindex import build_repo  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--src", type=Path, default=Path("."))
    ap.add_argument("--course", default=None, help="course name (then --src is the course folder)")
    ap.add_argument("--trust", type=int, default=2, choices=range(4))
    ap.add_argument("--type", default=None, help="force source_type (e.g. slides)")
    ap.add_argument("--no-index", action="store_true", help="SQLite only; run reindex.py later")
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--rescan-flags",
        action="store_true",
        help="recompute instruction-pattern flags on all stored chunks, then exit",
    )
    args = ap.parse_args()
    if args.rescan_flags:
        s = get_settings()
        upgrade_to_head(s.sync_database_url)
        engine = make_engine(s.database_url_resolved)
        try:
            async with make_session_factory(engine)() as db:
                n, changed = await rescan_flags(db)
        finally:
            await engine.dispose()
        print(f"rescanned {n} chunks, {changed} changed")
        return 0
    if not args.src.exists():
        print(f"not found: {args.src}", file=sys.stderr)
        return 2
    s = get_settings()
    upgrade_to_head(s.sync_database_url)
    engine = make_engine(s.database_url_resolved)
    repo = None
    try:
        async with make_session_factory(engine)() as db:
            if not args.no_index:
                repo = await build_repo(db, s)
            report = await ingest_path(
                db,
                args.src,
                course=args.course,
                source_type=args.type,
                trust_tier=args.trust,
                repo=repo,
            )
    finally:
        if repo is not None:
            await repo.client.close()
        await engine.dispose()
    summary = report.summary()
    if args.json:
        skipped = [{"path": sk.path, "reason": sk.reason} for sk in report.skipped]
        print(json.dumps({**summary, "skipped_files": skipped}, indent=2))
        return 0
    for r in report.results:
        mark = "new " if r.changed else "same"
        extra = f" dedup={r.deduped} flagged={r.flagged}" if r.changed else ""
        print(f"[{mark}] v{r.version} {r.chunks:3d} chunks  {r.course} › {r.title}{extra}")
    for sk in report.skipped:
        print(f"[skip] {sk.path}: {sk.reason}")
    print(
        f"{summary['documents']} documents ({summary['new_versions']} new versions), "
        f"{summary['chunks']} chunks, {summary['deduped']} deduped, {summary['flagged']} flagged, "
        f"{summary['indexed']} indexed; courses: {', '.join(summary['courses'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
