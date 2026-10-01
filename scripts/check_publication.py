#!/usr/bin/env python3
"""Inspect the Git index before publication; never rely on unstaged cleanup."""

import argparse
import hashlib
import re
import subprocess
from pathlib import Path

# Owner-prohibited source-provider identifiers. Digests keep the identifiers themselves
# out of public code/docs while allowing case-insensitive token checks (including URLs).
PROHIBITED_TOKEN_HASHES = frozenset({
    "583e17796e6a79e518b3b699d5fac2e9b758fea3904fed4937af0753e2c26759",
    "016d473857f1029884ec80ede8ae486f33d2fdad9411d63cd2aab11097ee997c",
})
PRIVATE_PREFIXES = ("data/", "frontend/public/local-learning/", "private/", "private-state/", "local-only/")


def inspect_blob(name: str, content: bytes, prohibited: frozenset[str] = PROHIBITED_TOKEN_HASHES) -> list[str]:
    """Return reasons only, without copying private content into logs."""
    path = Path(name)
    reasons = []
    if (name.startswith(PRIVATE_PREFIXES)
        or path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}
        or name.endswith((".db-wal", ".db-shm", ".sqlite-wal", ".sqlite-shm"))
        or path.name == ".env"):
        reasons.append("private runtime path")
    if content.startswith(b"SQLite format 3\0"):
        reasons.append("SQLite database content")
    # Scan ASCII identifier tokens even in binary blobs; no lossy decoding is needed.
    tokens = re.findall(rb"[A-Za-z]+", name.encode() + b"\n" + content)
    if any(hashlib.sha256(token.lower()).hexdigest() in prohibited for token in set(tokens)):
        reasons.append("prohibited source identifier")
    return reasons


def check_index(root: Path) -> list[str]:
    entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root)
    failures = []
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        info, raw_name = entry.split(b"\t", 1)
        mode, oid, stage = info.split()
        name = raw_name.decode("utf-8", errors="replace")
        if stage != b"0":
            failures.append(f"{name}: unresolved merge")
            continue
        if mode == b"160000":
            failures.append(f"{name}: submodule content requires separate publication review")
            continue
        content = subprocess.check_output(["git", "cat-file", "blob", oid.decode()], cwd=root)
        for reason in inspect_blob(name, content):
            failures.append(f"{name}: {reason}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    failures = check_index(args.repository)
    if failures:
        raise SystemExit("Publication refused:\n" + "\n".join(failures))
    print("Publication check passed: staged files contain no prohibited runtime assets or source identifiers.")


if __name__ == "__main__":
    main()
