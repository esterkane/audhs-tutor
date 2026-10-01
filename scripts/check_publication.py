#!/usr/bin/env python3
"""Reject runtime databases and private learning assets from a Git publication."""
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
failures = []
for name in filter(None, paths):
    p = root / name
    if not p.is_file():
        continue
    if (
        name.startswith(("data/", "frontend/public/local-learning/", "private/", "local-only/"))
        or p.suffix.lower() in {".db", ".sqlite", ".sqlite3"}
        or name.endswith((".db-wal", ".db-shm", ".sqlite-wal", ".sqlite-shm"))
        or p.name == ".env"
    ):
        failures.append(name)
        continue
    with p.open("rb") as f:
        if f.read(16) == b"SQLite format 3\0":
            failures.append(name)
if failures:
    raise SystemExit("Private runtime content cannot be published:\n" + "\n".join(failures))
print("Publication check passed: no tracked runtime database or private learning assets.")
