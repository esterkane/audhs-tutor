#!/usr/bin/env python3
"""Curate and draft one course — as a dry run on a private snapshot of the database by default.

  draft_course.py --course NAME [--section S] [--snapshot | --live] [--json]

With `--snapshot` (the default) the configured SQLite database is copied with the online-backup
API into a temp file and everything happens there: the source roles are listed (owner decisions
and suggestions), a deterministic draft is proposed for the section (or every section), the
validation problems are printed, every citation is checked, and the live database is never
touched. `--live` writes the draft(s) into the configured database as the Curriculum screen
would — still a *draft*: nothing is published, no trust tier changes, no learning progress moves.
No model is called (deterministic drafting only); use the Curriculum screen's model option for
proposals from the routed local model.
"""

import argparse
import asyncio
import contextlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.kernel import curriculum  # noqa: E402
from app.kernel.learner import get_or_create_owner  # noqa: E402


def _snapshot(sync_url: str, dest: Path) -> str:
    """Online backup of the configured DB into `dest`; the source is opened read-only so a wrong
    DATABASE_URL can never create an empty database by accident."""
    src = sync_url.replace("sqlite:///", "", 1)
    with (
        contextlib.closing(sqlite3.connect(f"file:{src}?mode=ro", uri=True)) as a,
        contextlib.closing(sqlite3.connect(dest)) as b,
    ):
        a.backup(b)
    return f"sqlite+aiosqlite:///{dest}"


async def run(args: argparse.Namespace) -> dict[str, Any]:
    s = get_settings()
    if args.live:
        url = s.database_url_resolved
        upgrade_to_head(s.sync_database_url)
        return await _run_on(url, args)
    # the snapshot is a plaintext copy of the learner's database: it lives only for this run
    with tempfile.TemporaryDirectory(prefix="audhs-draft-snapshot-") as td:
        url = _snapshot(s.sync_database_url, Path(td) / "snapshot.db")
        upgrade_to_head(url.replace("+aiosqlite", ""))
        return await _run_on(url, args)


async def _run_on(url: str, args: argparse.Namespace) -> dict[str, Any]:
    engine = make_engine(url)
    out: dict[str, Any] = {
        "course": args.course,
        "mode": "live" if args.live else "snapshot",
        "sections": [],
    }
    try:
        async with make_session_factory(engine)() as db:
            owner = await get_or_create_owner(db)
            sources = await curriculum.course_sources(db, args.course)
            if not sources:
                raise SystemExit(f"no documents for course {args.course!r}")
            counts: dict[str, int] = {}
            for r in sources:
                counts[str(r["role"])] = counts.get(str(r["role"]), 0) + 1
            out["sources"] = {
                "documents": len(sources),
                "roles": counts,
                "owner_decisions": sum(1 for r in sources if r["decided_by"] == "owner"),
                "suggested_supplemental": [
                    {"title": r["title"], "reason": r["reason"]}
                    for r in sources
                    if r["role"] != "primary" and r["decided_by"] == "suggested"
                ],
            }
            sections = (
                [{"section": args.section}]
                if args.section is not None
                else await curriculum.sections_of(db, args.course)
            )
            open_drafts = {
                d.section
                for d in await curriculum.list_drafts(db, owner.id)
                if d.course == args.course and d.status == "draft"
            }
            for sec in sections:
                entry: dict[str, Any] = {"section": sec["section"]}
                if args.live and sec["section"] in open_drafts:
                    entry["skipped"] = "an open draft for this section already exists"
                    out["sections"].append(entry)
                    continue
                try:
                    draft = await curriculum.create_draft(
                        db, owner.id, course=args.course, section=sec["section"]
                    )
                except ValueError as e:
                    entry["refused"] = str(e)
                    out["sections"].append(entry)
                    continue
                payload = draft.payload_json
                cited = {c for o in payload["learning_objects"] for c in o["sources"]}
                unresolved = 0
                for cid in cited:
                    if await curriculum.passage(db, cid) is None:
                        unresolved += 1
                probs = draft.validation_json
                entry.update(
                    {
                        "draft_id": draft.id,
                        "skills": len(payload["skills"]),
                        "learning_objects": len(payload["learning_objects"]),
                        "assessments": len(payload["assessments"]),
                        "citations": len(cited),
                        "citations_unresolved": unresolved,
                        "errors": sum(1 for p in probs if p["level"] == "error"),
                        "warnings": sum(1 for p in probs if p["level"] == "warning"),
                        "notes": [p["message"] for p in probs if p["level"] == "info"],
                        "open_questions": sorted(
                            {p["message"] for p in probs if p["level"] == "warning"}
                        )[:12],
                    }
                )
                out["sections"].append(entry)
    finally:
        await engine.dispose()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--course", required=True)
    ap.add_argument("--section", default=None)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--snapshot", action="store_true", help="dry run on a copy (default)")
    g.add_argument("--live", action="store_true", help="write drafts into the configured DB")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    out = asyncio.run(run(args))
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    src = out["sources"]
    print(
        f"{out['course']} ({out['mode']}): {src['documents']} documents — "
        + ", ".join(f"{k} {v}" for k, v in sorted(src["roles"].items()))
        + f"; {src['owner_decisions']} owner decision(s)"
    )
    shown = src["suggested_supplemental"][:10]
    for s in shown:
        print(f"  suggested {s['title']}: {s['reason']}")
    if len(src["suggested_supplemental"]) > len(shown):
        print(f"  … {len(src['suggested_supplemental']) - len(shown)} more (use --json)")
    for e in out["sections"]:
        if "refused" in e:
            print(f"- {e['section']}: refused — {e['refused']}")
            continue
        if "skipped" in e:
            print(f"- {e['section']}: skipped — {e['skipped']}")
            continue
        print(
            f"- {e['section']}: {e['skills']} skills, {e['assessments']} cloze items, "
            f"{e['citations']} citations ({e['citations_unresolved']} unresolved), "
            f"{e['errors']} errors, {e['warnings']} warnings"
        )
        for n in e["notes"][:6]:
            print(f"    {n}")
        if len(e["notes"]) > 6:
            print(f"    … {len(e['notes']) - 6} more notes (use --json)")
        for q in e["open_questions"]:
            print(f"    open: {q}")
    if out["mode"] == "snapshot":
        print("dry run on a snapshot — the live database was not touched", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
