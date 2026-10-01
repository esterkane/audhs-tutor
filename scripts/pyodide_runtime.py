#!/usr/bin/env python3
"""Install the pinned Pyodide runtime for the code exercise (ADR-0013: locally served, no CDN).

  pyodide_runtime.py install [--packages numpy] [--dest frontend/public/pyodide] [--refresh-manifest]
  pyodide_runtime.py verify  [--dest …]

Downloads the core files of one pinned Pyodide release plus the wheels the exercises need (with
their dependencies from `pyodide-lock.json`) into the frontend's public folder, which Vite serves
at `/pyodide/` and which is git-ignored. `frontend/pyodide.manifest.json` (committed) pins the
version and the sha256 of every file: the first install writes it, every later install and
`verify` check against it and refuse a mismatch. Nothing here runs at request time — the browser
never falls back to a CDN; a missing runtime is an explicit error in the exercise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.27.8"
INDEX_URL = f"https://cdn.jsdelivr.net/pyodide/v{VERSION}/full/"
CORE_FILES = (
    "pyodide.js",
    "pyodide.asm.js",
    "pyodide.asm.wasm",
    "python_stdlib.zip",
    "pyodide-lock.json",
)
DEFAULT_PACKAGES = ("numpy",)
DEFAULT_DEST = ROOT / "frontend" / "public" / "pyodide"
MANIFEST = ROOT / "frontend" / "pyodide.manifest.json"
MAX_FILE_BYTES = 64 << 20  # a single runtime file larger than this is not what we pinned
Fetcher = Callable[[str], bytes]


class Refusal(RuntimeError):
    """Refusal with a message for the operator (exit code 2)."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch_https(url: str) -> bytes:
    if not url.startswith("https://"):
        raise Refusal(f"refusing a non-https download: {url}")
    req = Request(url, headers={"User-Agent": "audhs-tutor pyodide_runtime"})
    with urlopen(req, timeout=60) as r:  # noqa: S310
        data: bytes = r.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise Refusal(f"{url} is larger than {MAX_FILE_BYTES >> 20} MiB — not a pinned file")
    return data


def resolve_packages(lock: dict[str, Any], names: tuple[str, ...]) -> list[tuple[str, str]]:
    """`(file_name, sha256)` for every requested package and its transitive dependencies,
    in dependency order, from a `pyodide-lock.json`."""
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        raise Refusal("pyodide-lock.json has no packages table")
    order: list[tuple[str, str]] = []
    seen: set[str] = set()

    def visit(name: str, chain: tuple[str, ...]) -> None:
        if name in seen:
            return
        if name in chain:
            raise Refusal(f"dependency cycle in pyodide-lock.json: {' → '.join(chain + (name,))}")
        entry = packages.get(name)
        if not isinstance(entry, dict):
            raise Refusal(f"package {name!r} is not in pyodide-lock.json for {VERSION}")
        for dep in entry.get("depends", []):
            visit(str(dep), chain + (name,))
        file_name, sha = entry.get("file_name"), entry.get("sha256")
        if not isinstance(file_name, str) or not isinstance(sha, str) or len(sha) != 64:
            raise Refusal(f"package {name!r} has no file name or sha256 in the lock")
        if Path(file_name).name != file_name or file_name.startswith(".") or "\\" in file_name:
            raise Refusal(f"package {name!r} has an unsafe file name {file_name!r}")
        seen.add(name)
        order.append((file_name, sha))

    for n in names:
        visit(n, ())
    return order


def _write_atomic(dest: Path, data: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{dest.name}.", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def load_manifest(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    m = json.loads(path.read_text())
    if not isinstance(m, dict) or not isinstance(m.get("files"), dict):
        raise Refusal(f"{path} is not a runtime manifest")
    return m


def verify(dest: Path, manifest_path: Path = MANIFEST) -> list[str]:
    """Problems with the installed runtime versus the committed manifest (empty = ok)."""
    m = load_manifest(manifest_path)
    if m is None:
        return [f"no manifest at {manifest_path}: run `install` first"]
    problems: list[str] = []
    if m.get("version") != VERSION:
        problems.append(f"manifest pins {m.get('version')!r}, this script pins {VERSION!r}")
    for name, info in m["files"].items():
        p = dest / name
        if not p.is_file():
            problems.append(f"missing {name}")
        elif sha256_file(p) != info.get("sha256"):
            problems.append(f"sha256 mismatch for {name}")
    return problems


def install(
    dest: Path = DEFAULT_DEST,
    packages: tuple[str, ...] = DEFAULT_PACKAGES,
    *,
    manifest_path: Path = MANIFEST,
    refresh_manifest: bool = False,
    fetch: Fetcher = fetch_https,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Download what is missing or wrong, verify every file, write/refresh the manifest."""
    manifest = None if refresh_manifest else load_manifest(manifest_path)
    if manifest is not None and manifest.get("version") != VERSION:
        raise Refusal(
            f"{manifest_path} pins Pyodide {manifest.get('version')!r} but this script pins "
            f"{VERSION!r}; run with --refresh-manifest after reviewing the change"
        )
    pinned: dict[str, str] = (
        {k: str(v["sha256"]) for k, v in manifest["files"].items()} if manifest else {}
    )

    def ensure(name: str, expected: str | None) -> tuple[str, int]:
        p = dest / name
        if expected is not None and p.is_file():
            have = sha256_file(p)
            if have == expected:
                return have, p.stat().st_size
        # no pin for this file (first install / re-pin): never trust what is already on disk
        data = fetch(INDEX_URL + name)
        got = sha256_bytes(data)
        if expected is not None and got != expected:
            raise Refusal(
                f"{name}: sha256 {got[:12]}… does not match the pinned {expected[:12]}… "
                "(the pinned release changed upstream, or the download was tampered with)"
            )
        _write_atomic(p, data)
        log(f"  fetched {name} ({len(data) >> 10} KiB)")
        return got, len(data)

    files: dict[str, dict[str, Any]] = {}
    for name in CORE_FILES:
        sha, size = ensure(name, pinned.get(name))
        files[name] = {"sha256": sha, "size": size}
    lock = json.loads((dest / "pyodide-lock.json").read_text())
    if lock.get("info", {}).get("version") != VERSION:
        raise Refusal(
            "pyodide-lock.json is not the pinned version — delete the runtime folder "
            f"({dest}) and re-run"
        )
    wheels = resolve_packages(lock, packages)
    for file_name, lock_sha in wheels:
        expected = pinned.get(file_name, lock_sha)
        if expected != lock_sha:
            raise Refusal(f"{file_name}: manifest and lock disagree on the sha256")
        sha, size = ensure(file_name, expected)
        files[file_name] = {"sha256": sha, "size": size}
    if manifest is not None:
        stale = set(manifest["files"]) - set(files)
        if stale:
            raise Refusal(
                f"manifest lists files this install did not produce: {sorted(stale)[:3]} — "
                "run with --refresh-manifest after reviewing the change"
            )
    new_manifest = {
        "version": VERSION,
        "index_url": INDEX_URL,
        "packages": list(packages),
        "files": dict(sorted(files.items())),
    }
    if manifest is None or manifest.get("files") != new_manifest["files"]:
        _write_atomic(manifest_path, (json.dumps(new_manifest, indent=2) + "\n").encode())
        log(f"  wrote {manifest_path}")
    return new_manifest


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("install", help="download what is missing, verify everything, pin it")
    i.add_argument("--packages", default=",".join(DEFAULT_PACKAGES))
    i.add_argument("--dest", default=str(DEFAULT_DEST))
    i.add_argument("--refresh-manifest", action="store_true", help="re-pin after a reviewed change")
    v = sub.add_parser("verify", help="check the installed runtime against the manifest (offline)")
    v.add_argument("--dest", default=str(DEFAULT_DEST))
    args = ap.parse_args()
    try:
        if args.cmd == "install":
            pk = tuple(p.strip() for p in args.packages.split(",") if p.strip())
            m = install(Path(args.dest), pk, refresh_manifest=args.refresh_manifest)
            total = sum(int(f["size"]) for f in m["files"].values())
            print(
                f"ok: Pyodide {VERSION} + {', '.join(m['packages'])} in {args.dest} "
                f"({len(m['files'])} files, {total >> 20} MiB), served at /pyodide/"
            )
        else:
            problems = verify(Path(args.dest))
            if problems:
                print("runtime problems:\n  " + "\n  ".join(problems), file=sys.stderr)
                return 2
            print(f"ok: Pyodide {VERSION} verified in {args.dest}")
    except Refusal as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
