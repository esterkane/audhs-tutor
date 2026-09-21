#!/usr/bin/env python3
"""Backup / inspect / restore one installation (P5).

  backup.py create  --out FILE [--scope learner|full] [--include-transcripts] [--db sqlite:///…]
  backup.py inspect FILE
  backup.py restore FILE --target DIR        (DIR must not exist or be empty; the live DB is untouched)

`learner` (default) leaves purchased course text out; `full` is private recovery only.
Archives are NOT encrypted (see docs/RECOVERY.md).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.backup import (  # noqa: E402
    RECONSTRUCTION_SETTINGS,
    BackupError,
    create_backup,
    inspect_backup,
    restore_backup,
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create", help="write a new backup archive (never overwrites)")
    c.add_argument("--out", required=True)
    c.add_argument("--scope", choices=("learner", "full"), default="learner")
    c.add_argument("--include-transcripts", action="store_true", help="add the STT cache")
    c.add_argument("--db", help="sqlite:///… URL (default: the configured database)")
    i = sub.add_parser("inspect", help="validate the manifest and every checksum")
    i.add_argument("file")
    r = sub.add_parser("restore", help="restore into an empty target folder")
    r.add_argument("file")
    r.add_argument("--target", required=True)
    args = ap.parse_args()
    settings = get_settings()
    try:
        if args.cmd == "create":
            if args.scope == "full":
                print(
                    "note: scope=full includes the corpus text of purchased courses — "
                    "private recovery only, never share this file",
                    file=sys.stderr,
                )
            rep = create_backup(
                args.db or settings.sync_database_url,
                Path(args.out),
                scope=args.scope,
                transcripts_dir=settings.transcript_cache_dir_resolved
                if args.include_transcripts
                else None,
                settings_snapshot=settings.model_dump(include=set(RECONSTRUCTION_SETTINGS)),
            )
            tables = rep.manifest["database"]["tables"]
            print(
                f"wrote {rep.path} · scope {args.scope} · {len(rep.manifest['files'])} files · "
                f"{sum(tables.values())} rows in {len(tables)} tables · not encrypted"
            )
        elif args.cmd == "inspect":
            m = inspect_backup(Path(args.file))
            print(json.dumps({k: v for k, v in m.items() if k != "sources"}, indent=2))
            print(
                f"ok: {len(m['files'])} files verified; {len(m['sources']['documents'])} documents referenced"
            )
        else:
            rep = restore_backup(Path(args.file), Path(args.target))
            print(f"restored into {rep.path} — read {rep.path / 'RESTORE-NOTES.md'} next")
    except BackupError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
