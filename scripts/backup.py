#!/usr/bin/env python3
"""Backup / inspect / restore one installation (P5).

  backup.py create  --out FILE [--scope learner|full] [--include-transcripts] [--db sqlite:///…]
                    [--encrypt [--password-file F]]
  backup.py inspect FILE [--password-file F]
  backup.py restore FILE --target DIR [--password-file F]   (DIR must not exist or be empty)

`learner` (default) leaves purchased course text out; `full` is private recovery only.
`--encrypt` wraps the archive in a password-based authenticated envelope (ADR-0012); without it the
archive is NOT encrypted (see docs/RECOVERY.md). The password is asked for interactively unless
`--password-file` names a file whose first line is the password; it is never stored.
"""

import argparse
import getpass
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db import backup_crypto  # noqa: E402
from app.db.backup import (  # noqa: E402
    RECONSTRUCTION_SETTINGS,
    BackupError,
    create_backup,
    inspect_backup,
    restore_backup,
)


def _password(path: str | None, *, confirm: bool) -> str:
    if path:
        f = Path(path).expanduser()
        try:
            if f.stat().st_mode & 0o077:
                print(f"note: {f} is readable by other users (chmod 600 it)", file=sys.stderr)
            pw = f.read_text(encoding="utf-8").splitlines()[0:1]
        except UnicodeDecodeError as e:
            raise BackupError(f"password file {path} is not UTF-8 text") from e
        except OSError as e:
            raise BackupError(f"cannot read password file {path}: {e}") from e
        if not pw or not pw[0]:
            raise BackupError(f"password file {path} is empty")
        return pw[0]
    if not sys.stdin.isatty():
        raise BackupError("no terminal for the password prompt: use --password-file")
    pw1 = getpass.getpass("backup password: ")
    if not pw1:
        raise BackupError("the password must not be empty")
    if confirm:
        if len(pw1) < 12:
            print("note: a password of 12+ characters is recommended", file=sys.stderr)
        if getpass.getpass("repeat password: ") != pw1:
            raise BackupError("passwords do not match")
    return pw1


def _password_if_encrypted(file: str, path: str | None) -> str | None:
    return _password(path, confirm=False) if backup_crypto.is_encrypted(Path(file)) else None


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
    c.add_argument("--encrypt", action="store_true", help="password-based authenticated envelope")
    c.add_argument("--password-file", help="file whose first line is the password (else: prompt)")
    i = sub.add_parser("inspect", help="validate the manifest and every checksum")
    i.add_argument("file")
    i.add_argument("--password-file")
    r = sub.add_parser("restore", help="restore into an empty target folder")
    r.add_argument("file")
    r.add_argument("--target", required=True)
    r.add_argument("--password-file")
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
            password = _password(args.password_file, confirm=True) if args.encrypt else None
            rep = create_backup(
                args.db or settings.sync_database_url,
                Path(args.out),
                scope=args.scope,
                transcripts_dir=settings.transcript_cache_dir_resolved
                if args.include_transcripts
                else None,
                settings_snapshot=settings.model_dump(include=set(RECONSTRUCTION_SETTINGS)),
                password=password,
            )
            tables = rep.manifest["database"]["tables"]
            print(
                f"wrote {rep.path} · scope {args.scope} · {len(rep.manifest['files'])} files · "
                f"{sum(tables.values())} rows in {len(tables)} tables · "
                f"{'encrypted (keep the password: it cannot be recovered)' if password else 'not encrypted'}"
            )
        elif args.cmd == "inspect":
            m = inspect_backup(
                Path(args.file), _password_if_encrypted(args.file, args.password_file)
            )
            print(json.dumps({k: v for k, v in m.items() if k != "sources"}, indent=2))
            print(
                f"ok: {len(m['files'])} files verified; {len(m['sources']['documents'])} documents "
                f"referenced; {'encrypted envelope' if m.get('_encrypted') else 'not encrypted'}"
            )
        else:
            rep = restore_backup(
                Path(args.file),
                Path(args.target),
                _password_if_encrypted(args.file, args.password_file),
            )
            print(f"restored into {rep.path} — read {rep.path / 'RESTORE-NOTES.md'} next")
    except BackupError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
