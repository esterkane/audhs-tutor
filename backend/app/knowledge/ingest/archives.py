"""Archives (zip, tar, tar.gz/.bz2/.xz) -> a safe temporary folder tree the normal file walker
can ingest. Guards: no absolute paths or `..` (zip-slip), no symlinks/devices, member and total
size caps, dot-folders / build folders / secret-looking files skipped, nested archives skipped
(one level is enough for a course download)."""

import re
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

ARCHIVE_SUFFIXES = {".zip", ".tar", ".tgz", ".tbz2", ".txz", ".tar.gz", ".tar.bz2", ".tar.xz"}
SKIP_DIRS = {
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".git",
    "dist",
    "build",
    ".ipynb_checkpoints",
    "site-packages",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "target",
    ".next",
    ".cache",
    "__MACOSX",
    "checkpoints",
    ".idea",
    ".vscode",
}
SECRET_NAMES = re.compile(
    r"^(\.env(\..*)?|.*\.(pem|key|p12|pfx|jks|keystore)|id_(rsa|dsa|ecdsa|ed25519)(\.pub)?"
    r"|.*credentials.*\.json|.*secrets?\.(json|ya?ml|toml)|\.netrc|\.npmrc|\.pypirc)$",
    re.I,
)
MAX_TOTAL_BYTES = 2_000_000_000
MAX_MEMBER_BYTES = 500_000_000
MAX_MEMBERS = 50_000


@dataclass
class ExtractReport:
    root: Path
    extracted: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)


def is_archive(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(s) for s in ARCHIVE_SUFFIXES)


def archive_stem(path: Path) -> str:
    name = path.name
    for s in sorted(ARCHIVE_SUFFIXES, key=len, reverse=True):
        if name.lower().endswith(s):
            name = name[: -len(s)]
            break
    return re.sub(r"\s*\(\d+\)$", "", name).strip()  # "agents-main (2)" → "agents-main"


def should_skip_relpath(rel: str) -> str | None:
    parts = PurePosixPath(rel).parts
    if not parts:
        return "empty"
    if any(p.startswith(".") and p not in (".", "..") for p in parts[:-1]) or any(
        p in SKIP_DIRS for p in parts[:-1]
    ):
        return "hidden or build folder"
    if SECRET_NAMES.match(parts[-1]):
        return "possible secret file"
    if parts[-1].startswith(".") and not parts[-1].lower().endswith((".md", ".txt")):
        return "dotfile"
    return None


def _safe_target(dest: Path, rel: str) -> Path | None:
    p = PurePosixPath(rel.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or not p.parts:
        return None
    target = (dest / Path(*p.parts)).resolve()
    return target if dest.resolve() in target.parents else None


def extract_archive(path: Path, dest: Path) -> ExtractReport:
    dest.mkdir(parents=True, exist_ok=True)
    report = ExtractReport(root=dest)
    total = 0
    if path.name.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            if len(infos) > MAX_MEMBERS:
                raise ValueError(f"archive has {len(infos)} members (cap {MAX_MEMBERS})")
            for info in infos:
                if info.is_dir():
                    continue
                reason = _member_reason(info.filename, info.file_size)
                target = _safe_target(dest, info.filename) if reason is None else None
                if reason is None and target is None:
                    reason = "unsafe path"
                if reason is not None:
                    report.skipped.append((info.filename, reason))
                    continue
                assert target is not None
                total += info.file_size
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("archive exceeds the 2 GB extraction cap")
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, target.open("wb") as out:
                    while chunk := src.read(1 << 20):
                        out.write(chunk)
                report.extracted += 1
    else:
        with tarfile.open(path) as t:
            count = 0
            for member in t:
                count += 1
                if count > MAX_MEMBERS:
                    raise ValueError(f"archive has more than {MAX_MEMBERS} members")
                if not member.isfile():
                    if not member.isdir():
                        report.skipped.append((member.name, "not a regular file"))
                    continue
                reason = _member_reason(member.name, member.size)
                target = _safe_target(dest, member.name) if reason is None else None
                if reason is None and target is None:
                    reason = "unsafe path"
                if reason is not None:
                    report.skipped.append((member.name, reason))
                    continue
                assert target is not None
                total += member.size
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("archive exceeds the 2 GB extraction cap")
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = t.extractfile(member)
                if stream is None:
                    continue
                with stream, target.open("wb") as out:
                    while chunk := stream.read(1 << 20):
                        out.write(chunk)
                report.extracted += 1
    return report


def _member_reason(name: str, size: int) -> str | None:
    if size > MAX_MEMBER_BYTES:
        return "member larger than 500 MB"
    if is_archive(Path(name)):
        return "nested archive"
    return should_skip_relpath(name)


def content_root(dest: Path, stem: str | None = None) -> Path:
    """GitHub-style downloads (`repo-main.zip` → `repo-main/…`) wrap everything in one folder
    named after the archive: step into it. Any other single folder is content (a section)."""
    entries = [p for p in dest.iterdir() if not p.name.startswith(".")]
    if len(entries) != 1 or not entries[0].is_dir():
        return dest
    if stem is None:
        return entries[0]
    norm = re.compile(r"[-_ ](main|master|develop|v?\d[\w.]*)$", re.I)
    a, b = norm.sub("", entries[0].name.lower()), norm.sub("", stem.lower())
    return entries[0] if a == b or a.startswith(b) or b.startswith(a) else dest
