"""Udemy "resources" exports (browser-extension downloads) ship a `manifest.json` per course:

    <Course--hash>/manifest.json
    <Course--hash>/Section 23 - Abschnitt 24- Title/Lecture 23-2 - 118. Lecture title/<file>

The manifest maps every saved file (`folder/filename`) to its clean course, section and lecture
titles, so provenance comes from there when it exists; the folder names are the fallback."""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_SECTION_DIR = re.compile(r"^Section\s+(\d+)\s*-\s*(?:Abschnitt\s+\d+\s*-\s*)?(.*\S)\s*$")
_SECTION_TITLE = re.compile(r"^(?:Abschnitt|Section)\s+(\d+)\s*[:\-]\s*(.*\S)\s*$")
_LECTURE_DIR = re.compile(r"^Lecture\s+\d+-\d+\s*-\s*(?:(\d+)\.\s*)?(.*\S)\s*$")
_LECTURE_TITLE = re.compile(r"^(?:(\d+)\.\s*)?(.*\S)\s*$")
_HASH_SUFFIX = re.compile(r"--[0-9a-f]{8,}$")


def clean_course_dir(name: str) -> str:
    return _HASH_SUFFIX.sub("", name).strip()


def parse_section_dir(name: str) -> tuple[int | None, str] | None:
    m = _SECTION_DIR.match(name)
    return (int(m.group(1)), m.group(2)) if m else None


def parse_lecture_dir(name: str) -> tuple[int | None, str] | None:
    m = _LECTURE_DIR.match(name)
    if not m:
        return None
    return (int(m.group(1)) if m.group(1) else None, m.group(2))


@lru_cache(maxsize=64)
def _load(manifest: str, mtime: float) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(Path(manifest).read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or not isinstance(data.get("resources"), dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in data["resources"].values():
        if not isinstance(r, dict) or not r.get("filename"):
            continue
        rel = f"{r.get('folder', '').strip('/')}/{r['filename']}".lstrip("/")
        out[rel] = {**r, "courseTitle": data.get("courseTitle") or r.get("courseTitle")}
        out[rel]["courseURL"] = data.get("courseURL")
    return out


def find_course_dir(path: Path, stop: Path | None) -> Path | None:
    """Nearest ancestor holding a manifest.json (search stops at `stop`)."""
    for parent in path.parents:
        if (parent / "manifest.json").is_file():
            return parent
        if stop is not None and parent == stop:
            break
    return None


def provenance_from_manifest(path: Path, stop: Path | None = None) -> dict[str, Any] | None:
    course_dir = find_course_dir(path.resolve(), stop.resolve() if stop else None)
    if course_dir is None:
        return None
    manifest = course_dir / "manifest.json"
    entries = _load(str(manifest), manifest.stat().st_mtime)
    rel = path.resolve().relative_to(course_dir).as_posix()
    r = entries.get(rel)
    if r is None:
        return None
    meta: dict[str, Any] = {"course_url": r.get("courseURL"), "resource_label": r.get("label")}
    section_no: int | None = None
    section = str(r.get("sectionTitle") or "")
    m = _SECTION_TITLE.match(section)
    if m:
        section_no, section = int(m.group(1)), m.group(2)
    folder_section = (
        parse_section_dir(Path(str(r.get("folder", ""))).parts[0]) if r.get("folder") else None
    )
    if folder_section and folder_section[0] is not None:
        section_no = folder_section[0]  # the English "Section N" numbering
    lecture_no: int | None = None
    lecture = str(r.get("lectureTitle") or "")
    m = _LECTURE_TITLE.match(lecture)
    if m:
        lecture_no = int(m.group(1)) if m.group(1) else None
        lecture = m.group(2)
    if section_no is not None:
        meta["section_no"] = section_no
    if lecture_no is not None:
        meta["lecture_no"] = lecture_no
    return {
        "course": str(r.get("courseTitle") or clean_course_dir(course_dir.name)),
        "section": section or None,
        "lecture": lecture or None,
        "title": Path(str(r.get("label") or r["filename"])).stem,
        **meta,
    }
