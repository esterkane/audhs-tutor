#!/usr/bin/env python3
"""Ingest course material into SQLite and the retrieval index.

usage: ingest.py --src PATH [--course NAME] [--trust 0-3] [--type TYPE] [--no-index] [--json]
                 [--language xx] [--no-media] [--capabilities] [--resume | --resume-run ID]
                 [--runs]

PATH is a file or a folder laid out like a Udemy export: <src>/<Course>/<NN - Section>/<NNN - Lecture>.ext
With --course, <src> itself is the course folder. Formats: captions/transcripts (vtt srt sbv ass ttml
json tsv timestamped txt), documents (pdf docx odt rtf tex xlsx ods csv), slides (pptx odp), epub, html,
markdown/rst/org/adoc, notebooks and source code, zip/tar archives, audio/video (transcribed with the
registry STT model) and images (read by the registry vision model). `--capabilities` shows what this
machine can do right now. Idempotent: unchanged files are no-ops; changed files get a new version.
Trust is decided here, never read from the files (ADR-0008). Default trust 2 = purchased material.
Progress goes to stderr per file and per archive member; every file ends in one outcome class
(imported, unchanged, reference_only, no_content, unsupported, gated, retryable_error,
access_blocked, parser_error). Ctrl-C leaves the run marked `interrupted`; `--resume` continues
the newest interrupted run over the same path without redoing what it finished.
"""

import argparse
import asyncio
import json
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.models import IngestRun  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.knowledge.ingest.runtime import capabilities, default_options  # noqa: E402
from app.knowledge.ingest.service import (  # noqa: E402
    OUTCOMES,
    IngestProgress,
    ingest_path,
    latest_resumable_run,
    rescan_flags,
)


def _progress_line(p: IngestProgress) -> str:
    where = p.current.rsplit("/", 2)
    short = "/".join(where[-2:]) if len(where) > 1 else p.current
    if p.archive:
        return f"[{p.done + 1}/{p.total}] {p.archive} › member {p.member_done + 1}/{p.member_total} {short}"
    return f"[{p.done + 1}/{p.total}] {short}"


def _print_progress(p: IngestProgress) -> None:
    print(_progress_line(p), file=sys.stderr, flush=True)


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
    ap.add_argument("--language", default=None, help="force STT language (ISO code), default auto")
    ap.add_argument(
        "--no-media", action="store_true", help="skip audio/video/images (list them as skipped)"
    )
    ap.add_argument(
        "--capabilities", action="store_true", help="show supported formats + runtime readiness"
    )
    ap.add_argument(
        "--retranscribe",
        action="store_true",
        help="re-run STT/vision on unchanged media (after a model change; ignores the hash shortcut)",
    )
    ap.add_argument(
        "--resume", action="store_true", help="continue the newest interrupted run over --src"
    )
    ap.add_argument("--resume-run", default=None, help="continue this interrupted run id")
    ap.add_argument("--runs", action="store_true", help="list recorded runs, then exit")
    ap.add_argument("--quiet", action="store_true", help="no per-file progress on stderr")
    args = ap.parse_args()
    if args.runs:
        s = get_settings()
        upgrade_to_head(s.sync_database_url)
        engine = make_engine(s.database_url_resolved)
        try:
            async with make_session_factory(engine)() as db:
                rows = (
                    (
                        await db.execute(
                            select(IngestRun).order_by(IngestRun.started_at.desc()).limit(20)
                        )
                    )
                    .scalars()
                    .all()
                )
                for run_row in rows:
                    print(
                        f"{run_row.id}  {run_row.status:11s} "
                        f"{run_row.files_done}/{run_row.files_total}  "
                        f"{run_row.started_at[:19]}  {run_row.src}"
                        + (f"  (resumed {run_row.resumed_from})" if run_row.resumed_from else "")
                    )
        finally:
            await engine.dispose()
        return 0
    if args.capabilities:
        s = get_settings()
        upgrade_to_head(s.sync_database_url)
        engine = make_engine(s.database_url_resolved)
        try:
            async with make_session_factory(engine)() as db:
                caps = await capabilities(db, s)
        finally:
            await engine.dispose()
        if args.json:
            print(json.dumps(caps, indent=2))
            return 0
        for group, suffixes in caps["formats"].items():
            print(f"{group:24s} {' '.join(suffixes)}")
        for label, tool in (("speech-to-text", caps["stt"]), ("images (vision)", caps["vision"])):
            state = "READY" if tool["ready"] else "not ready"
            print(f"{label:24s} {state} — {tool['detail']}")
        print(f"{'audio decoder':24s} {caps['audio_decoder'] or 'none (brew install ffmpeg)'}")
        print(f"{'legacy office (.doc/.ppt)':24s} {caps['legacy_office'] or 'none'}")
        print(
            f"{'unsupported':24s} "
            + ", ".join(f"{k} → {v}" for k, v in caps["unsupported"].items())
        )
        return 0
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
            options = await default_options(
                db,
                s,
                media=not args.no_media,
                language=args.language,
                force_media=args.retranscribe,
            )
            resume_id = args.resume_run
            if args.resume and resume_id is None:
                prev = await latest_resumable_run(db, args.src, args.course)
                if prev is None:
                    print(f"nothing to resume for {args.src}", file=sys.stderr)
                    return 2
                resume_id = prev.id
            if resume_id is not None:
                prev = await db.get(IngestRun, resume_id)
                if prev is None or prev.status != "interrupted":
                    print(f"run {resume_id} is not an interrupted run", file=sys.stderr)
                    return 2
                # a resume keeps the run's own settings so one course never splits across tiers
                kept = dict(prev.options_json or {})
                args.trust = int(kept.get("trust_tier", args.trust))
                args.type = kept.get("source_type", args.type)
                args.course = prev.course
                options = await default_options(
                    db,
                    s,
                    media=bool(kept.get("media", not args.no_media)),
                    language=kept.get("language", args.language),
                    force_media=args.retranscribe,
                )
                print(
                    f"resuming run {resume_id} ({prev.files_done}/{prev.files_total} done, "
                    f"trust {args.trust})",
                    file=sys.stderr,
                )
            options.progress = None if args.quiet else _print_progress
            # Ctrl-C = clean stop after the current file (a task cancel could land inside an
            # aiosqlite commit); a second Ctrl-C falls back to the default and aborts
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()

            def on_sigint() -> None:
                if stop.is_set():
                    loop.remove_signal_handler(signal.SIGINT)
                    raise KeyboardInterrupt
                print("\nstopping after the current file… (Ctrl-C again to abort)", file=sys.stderr)
                stop.set()

            loop.add_signal_handler(signal.SIGINT, on_sigint)
            options.should_stop = stop.is_set
            try:
                report = await ingest_path(
                    db,
                    args.src,
                    course=args.course,
                    source_type=args.type,
                    trust_tier=args.trust,
                    repo=repo,
                    options=options,
                    resume_run_id=resume_id,
                )
            finally:
                loop.remove_signal_handler(signal.SIGINT)
    finally:
        if repo is not None:
            await repo.client.close()
        await engine.dispose()
    summary = report.summary()
    counts = summary["outcomes"]
    if args.json:
        skipped = [
            {"path": sk.path, "reason": sk.reason, "outcome": sk.outcome} for sk in report.skipped
        ]
        print(json.dumps({**summary, "skipped_files": skipped}, indent=2))
        return 0
    for r in report.results:
        mark = {"imported": "new ", "unchanged": "same", "reference_only": "refs"}[r.outcome]
        extra = f" dedup={r.deduped} flagged={r.flagged}" if r.changed else ""
        if r.transcribed_seconds is not None:
            extra += f" transcribed={r.transcribed_seconds:.0f}s"
        print(f"[{mark}] v{r.version} {r.chunks:3d} chunks  {r.course} › {r.title}{extra}")
    for sk in report.skipped:
        print(f"[{sk.outcome}] {sk.path}: {sk.reason}")
    print(
        f"run {report.run_id}: {summary['files']} files — "
        + ", ".join(f"{k} {counts[k]}" for k in OUTCOMES if counts[k])
        + (f"; {report.resumed} already done before the resume" if report.resumed else "")
    )
    print(
        f"{summary['documents']} documents ({summary['new_versions']} new versions), "
        f"{summary['chunks']} chunks, {summary['deduped']} deduped, {summary['flagged']} flagged, "
        f"{summary['indexed']} indexed; courses: {', '.join(summary['courses'])}"
        + (
            f"; {summary['transcribed_media']} media transcribed ({summary['audio_seconds']:.0f} s)"
            if summary["transcribed_media"]
            else ""
        )
        + (f"; {summary['images_read']} images read" if summary["images_read"] else "")
    )
    if report.interrupted:
        print(
            f'stopped early — continue with: make ingest src="{args.src}" resume=1',
            file=sys.stderr,
        )
        return 130
    needs_owner = [sk for sk in report.skipped if sk.outcome in ("access_blocked", "parser_error")]
    if needs_owner:
        print(f"{len(needs_owner)} file(s) need attention (see outcomes above)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
