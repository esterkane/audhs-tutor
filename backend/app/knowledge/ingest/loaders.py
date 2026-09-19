"""File -> SourceDoc dispatch plus provenance derived from the Udemy folder layout:

    <root>/<Course>/<NN - Section>/<NNN - Lecture>.en.vtt

Numbers are kept in `meta` (section_no / lecture_no) and stripped from the labels. Trust is never
read from the file (the caller decides it, ADR-0008)."""

import re
from pathlib import Path
from typing import Any

from app.knowledge.ingest.captions import caption_blocks
from app.knowledge.ingest.markdown import parse_markdown
from app.knowledge.ingest.normalize import strip_invisible
from app.knowledge.ingest.notebook import notebook_blocks
from app.knowledge.ingest.pdf import pdf_blocks
from app.knowledge.ingest.types import Block, SourceDoc, content_hash
from app.knowledge.ingest.udemy_manifest import (
    clean_course_dir,
    parse_lecture_dir,
    parse_section_dir,
    provenance_from_manifest,
)

SUFFIX_TYPES: dict[str, str] = {
    ".vtt": "udemy_caption",
    ".srt": "udemy_caption",
    ".ipynb": "notebook",
    ".pdf": "pdf",
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
}
# document types we know about but do not parse: listed in the report as skipped, not ignored
KNOWN_UNSUPPORTED = {".docx", ".pptx", ".epub", ".doc", ".ppt"}
_NUMBERED = re.compile(r"^\s*(\d{1,4})\s*[-._:)]*\s+(.*\S)\s*$")
_LANG_SUFFIX = re.compile(r"[._-](en|de|es|fr|en-us|en-gb|auto)$", re.IGNORECASE)


def split_number(label: str) -> tuple[int | None, str]:
    m = _NUMBERED.match(label)
    if not m:
        return None, label.strip()
    return int(m.group(1)), m.group(2)


def clean_stem(path: Path) -> str:
    stem = path.stem
    if path.suffix.lower() in (".vtt", ".srt"):
        stem = _LANG_SUFFIX.sub("", stem)
    return stem


def provenance_from_path(
    path: Path, root: Path | None = None, *, course: str | None = None
) -> dict[str, Any]:
    """course/section/lecture (+ numbers) for a file. Order of authority: a Udemy `manifest.json`
    in an ancestor folder (clean titles), then the folder layout under `root`
    (`<Course>/<NN - Section>/<NNN - Lecture>.ext`, or the resources-export layout
    `<Course--hash>/Section N - Title/Lecture N-M - K. Title/<file>`)."""
    root = root.resolve() if root else path.resolve().parent
    p = path.resolve()
    from_manifest = provenance_from_manifest(p, root)
    if from_manifest is not None:
        if course is not None:
            from_manifest["course"] = course
        return from_manifest
    try:
        rel = p.relative_to(root)
        dirs = list(rel.parts[:-1])
    except ValueError:
        dirs = []
    meta: dict[str, Any] = {}
    if course is None:
        if dirs:
            course = clean_course_dir(dirs[0])
            dirs = dirs[1:]
        else:
            course = root.name
    section: str | None = None
    lecture_dir: tuple[int | None, str] | None = None
    if dirs and (lecture_dir := parse_lecture_dir(dirs[-1])) is not None:
        dirs = dirs[:-1]  # resources export: the lecture is a folder, files are its resources
    if dirs:
        parsed = parse_section_dir(dirs[0])
        no, label = parsed if parsed else split_number(dirs[0])
        section = " / ".join([label, *dirs[1:]])
        if no is not None:
            meta["section_no"] = no
    if lecture_dir is not None:
        lecture_no, lecture = lecture_dir
        meta["resource_label"] = clean_stem(path)
    else:
        lecture_no, lecture = split_number(clean_stem(path))
    if lecture_no is not None:
        meta["lecture_no"] = lecture_no
    out: dict[str, Any] = {"course": course, "section": section, "lecture": lecture, **meta}
    if lecture_dir is not None:
        out["title"] = clean_stem(path)
    return out


def source_type_for(path: Path, override: str | None = None) -> str | None:
    st = SUFFIX_TYPES.get(path.suffix.lower())
    if override:
        return override if st is not None else None  # an override relabels, it never widens
    if st == "pdf" and "slide" in path.stem.lower():
        return "slides"
    return st


def load_file(
    path: Path,
    *,
    root: Path | None = None,
    course: str | None = None,
    source_type: str | None = None,
    trust_front_matter: bool = False,
) -> SourceDoc:
    """Raises `ValueError` for unsupported suffixes and `PdfSupportMissing` without pypdf.
    Front matter (`uri`, `course`, `source_type`, …) is data from the file: it is used only when
    the caller says the file is owner-authored (`trust_front_matter`), never for course exports —
    otherwise a file could take over another document's identity."""
    st = source_type_for(path, source_type)
    if st is None:
        hint = " (export it to PDF)" if path.suffix.lower() in KNOWN_UNSUPPORTED else ""
        raise ValueError(f"unsupported file type: {path.suffix}{hint}")
    raw_bytes = path.read_bytes()
    prov = provenance_from_path(path, root, course=course)
    meta = {k: v for k, v in prov.items() if k not in ("course", "section", "lecture", "title")}
    default_title = str(prov.get("title") or prov["lecture"])
    uri = path.resolve().as_posix()
    if st == "markdown":
        md = parse_markdown(strip_invisible(raw_bytes.decode("utf-8", "replace")))
        m = md.meta if trust_front_matter else {}
        blocks = [
            Block(text=s.text, kind="prose", heading=s.heading, skill_slugs=s.skill_slugs)
            for s in md.sections
            if s.text.strip()
        ]
        if not blocks and md.body.strip():
            blocks = [Block(text=md.body.strip(), kind="prose")]
        return SourceDoc(
            title=md.title if md.title != "Untitled" else default_title,
            uri=str(m.get("uri") or uri),
            source_type=str(m.get("source_type") or "markdown"),
            blocks=blocks,
            content_hash=md.content_hash,
            course=course or m.get("course") or prov["course"],
            section=m.get("section") or prov["section"],
            # inside a course layout the file is the lecture; standalone notes use their
            # section headings as the lecture label per chunk (seed behaviour)
            lecture=m.get("lecture") or (prov["lecture"] if root is not None else None),
            meta={**meta, **{k: v for k, v in m.items() if k != "title"}},
        )
    text = (
        strip_invisible(raw_bytes.decode("utf-8", "replace"))
        if st != "pdf" and st != "slides"
        else ""
    )
    if st == "udemy_caption":
        blocks = caption_blocks(text)
    elif st == "notebook":
        blocks = notebook_blocks(text)
    elif st in ("pdf", "slides"):
        blocks = pdf_blocks(raw_bytes, kind="slide" if st == "slides" else "prose")
    else:  # text
        blocks = [Block(text=p.strip()) for p in re.split(r"\n\s*\n", text) if p.strip()]
    return SourceDoc(
        title=default_title,
        uri=uri,
        source_type=st,
        blocks=blocks,
        content_hash=content_hash(raw_bytes),
        course=prov["course"],
        section=prov["section"],
        lecture=prov["lecture"],
        meta=meta,
    )


def iter_source_files(src: Path) -> list[Path]:
    if src.is_file():
        return [src]
    files = [
        p
        for p in sorted(src.rglob("*"))
        if p.is_file()
        and (p.suffix.lower() in SUFFIX_TYPES or p.suffix.lower() in KNOWN_UNSUPPORTED)
        and not p.name.startswith(".")
    ]
    # Udemy exports often ship several caption languages: keep one per lecture (prefer English).
    seen: dict[tuple[Path, str], Path] = {}
    for p in files:
        key = (p.parent, clean_stem(p) + p.suffix.lower())
        if key not in seen or (".en" in p.stem.lower() and ".en" not in seen[key].stem.lower()):
            seen[key] = p
    return sorted(seen.values())
