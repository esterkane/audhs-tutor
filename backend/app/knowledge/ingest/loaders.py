"""File -> SourceDoc dispatch plus provenance derived from the Udemy folder layout:

    <root>/<Course>/<NN - Section>/<NNN - Lecture>.en.vtt

Numbers are kept in `meta` (section_no / lecture_no) and stripped from the labels. Trust is never
read from the file (the caller decides it, ADR-0008). Every format lands in the same `SourceDoc`
so the chunker, dedupe and index never know where the text came from."""

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from app.knowledge.ingest.archives import (
    ARCHIVE_SUFFIXES,
    SKIP_DIRS,
    is_archive,
    should_skip_relpath,
)
from app.knowledge.ingest.captions import caption_blocks
from app.knowledge.ingest.converters import convert_legacy_office
from app.knowledge.ingest.epub import epub_blocks
from app.knowledge.ingest.htmltext import html_blocks
from app.knowledge.ingest.latex import latex_blocks
from app.knowledge.ingest.markdown import parse_markdown
from app.knowledge.ingest.media import (
    AUDIO_SUFFIXES,
    DEFAULT_STT_HINT,
    MEDIA_SUFFIXES,
    Transcriber,
    transcribe_media,
    transcript_to_blocks,
)
from app.knowledge.ingest.normalize import strip_invisible
from app.knowledge.ingest.notebook import notebook_blocks
from app.knowledge.ingest.office import OFFICE_SUFFIXES, office_blocks
from app.knowledge.ingest.pdf import pdf_blocks
from app.knowledge.ingest.rtf import rtf_blocks
from app.knowledge.ingest.sourcecode import LANG_BY_SUFFIX, LOCKFILES, code_blocks, language_for
from app.knowledge.ingest.structured_text import STRUCTURED_SUFFIXES, structured_blocks
from app.knowledge.ingest.transcripts import TRANSCRIPT_SUFFIXES, transcript_blocks, transcript_cues
from app.knowledge.ingest.types import Block, SourceDoc, content_hash, file_hash
from app.knowledge.ingest.udemy_manifest import (
    clean_course_dir,
    parse_lecture_dir,
    parse_section_dir,
    provenance_from_manifest,
)
from app.knowledge.ingest.vision import (
    DEFAULT_VISION_HINT,
    IMAGE_SUFFIXES,
    ImageReader,
    read_image,
)

SUFFIX_TYPES: dict[str, str] = {
    ".vtt": "udemy_caption",
    ".srt": "udemy_caption",
    **{s: "transcript" for s in TRANSCRIPT_SUFFIXES},
    ".ipynb": "notebook",
    ".pdf": "pdf",
    ".md": "markdown",
    ".markdown": "markdown",
    ".mdx": "markdown",
    ".rmd": "markdown",
    ".qmd": "markdown",
    ".txt": "text",
    ".text": "text",
    ".rst": "text",
    ".org": "text",
    ".adoc": "text",
    ".asciidoc": "text",
    ".textile": "text",
    ".json": "text",  # sniffed: transcript / links list; other JSON is reported as skipped
    ".tsv": "document",
    ".csv": "document",
    ".xml": "transcript",  # TTML only
    ".docx": "document",
    ".docm": "document",
    ".odt": "document",
    ".rtf": "document",
    ".doc": "document",
    ".webarchive": "html",
    ".tex": "document",
    ".xlsx": "document",
    ".xlsm": "document",
    ".ods": "document",
    ".xls": "document",
    ".pptx": "slides",
    ".pptm": "slides",
    ".odp": "slides",
    ".ppt": "slides",
    ".key": "slides",
    ".pages": "document",
    ".numbers": "document",
    ".epub": "book",
    ".html": "html",
    ".htm": "html",
    ".xhtml": "html",
    **{s: "code" for s in LANG_BY_SUFFIX},
    **{s: "audio" for s in AUDIO_SUFFIXES},
    **{s: "video" for s in MEDIA_SUFFIXES - AUDIO_SUFFIXES},
    **{s: "image" for s in IMAGE_SUFFIXES},
}
# document types we know about but do not parse: listed in the report as skipped, not ignored
KNOWN_UNSUPPORTED: dict[str, str] = {
    ".7z": "extract it first (zip/tar are supported)",
    ".rar": "extract it first (zip/tar are supported)",
    ".mobi": "convert to EPUB (calibre)",
    ".azw3": "convert to EPUB (calibre)",
    ".djvu": "convert to PDF",
    ".xps": "convert to PDF",
    ".chm": "convert to PDF or HTML",
    ".svg": "export to PNG",
    ".psd": "export to PNG",
    ".ai": "export to PDF",
    ".exe": "not course material",
    ".dmg": "not course material",
}
IGNORED_NAMES = {  # platform metadata and tool configuration: never learning material
    "manifest.json",
    ".ds_store",
    "thumbs.db",
    "desktop.ini",
    "package.json",
    "tsconfig.json",
    "jsconfig.json",
    "composer.json",
    "langgraph.json",
    "vercel.json",
    "renovate.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
    "components.json",
    "biome.json",
}
FORMAT_GROUPS: dict[str, list[str]] = {
    "captions & transcripts": sorted(
        {
            ".vtt",
            ".srt",
            *TRANSCRIPT_SUFFIXES,
            ".xml (TTML)",
            ".json",
            ".tsv",
            ".csv",
            ".txt (timestamped)",
        }
    ),
    "documents": [
        ".pdf",
        ".docx",
        ".doc*",
        ".odt",
        ".rtf",
        ".tex",
        ".pages*",
        ".xlsx",
        ".ods",
        ".xls*",
        ".numbers*",
        ".csv",
        ".tsv",
    ],
    "slides": [".pptx", ".odp", ".ppt*", ".key*", ".pdf (slides)"],
    "books & web": [".epub", ".html", ".htm", ".xhtml", ".webarchive*"],
    "notes": [".md", ".mdx", ".rmd", ".qmd", ".txt", ".rst", ".org", ".adoc", ".textile"],
    "notebooks & code": [".ipynb", *sorted(LANG_BY_SUFFIX)],
    "archives": sorted(ARCHIVE_SUFFIXES),
    "audio (transcribed)": sorted(AUDIO_SUFFIXES),
    "video (transcribed)": sorted(MEDIA_SUFFIXES - AUDIO_SUFFIXES),
    "images (vision model)": sorted(IMAGE_SUFFIXES),
}
LEGACY_OFFICE = {".doc", ".ppt", ".xls", ".key", ".pages", ".numbers", ".webarchive"}
MAX_TEXT_BYTES = 20_000_000
_NUMBERED = re.compile(r"^\s*(\d{1,4})(?:\s*[-._:)]+\s*|\s+)(.*\S)\s*$")
_LANG_SUFFIX = re.compile(
    r"[._-](en|de|es|fr|it|pt|nl|pl|ru|ja|zh|ko|en-us|en-gb|auto)$", re.IGNORECASE
)


class SkipFile(ValueError):
    """The file is recognised but carries nothing to learn from (empty JSON, dataset, …)."""


def split_number(label: str) -> tuple[int | None, str]:
    m = _NUMBERED.match(label)
    if not m:
        return None, label.strip()
    return int(m.group(1)), m.group(2)


def clean_stem(path: Path) -> str:
    stem = path.stem
    if path.suffix.lower() in (".vtt", ".srt", *TRANSCRIPT_SUFFIXES, *MEDIA_SUFFIXES):
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
    lower = path.name.lower()
    st = SUFFIX_TYPES.get(path.suffix.lower())
    if st is None and language_for(lower) is not None:
        st = "code"  # Dockerfile, Makefile
    if override:
        return override if st is not None else None  # an override relabels, it never widens
    if st == "pdf" and "slide" in path.stem.lower():
        return "slides"
    return st


def is_expensive(path: Path) -> bool:
    """Loads that should be skipped entirely when the file's content hash is already stored."""
    s = path.suffix.lower()
    # not legacy Office: its title comes from the converted document, which the stub cannot know
    return s in MEDIA_SUFFIXES or s in IMAGE_SUFFIXES or s == ".pdf"


def stub_doc(
    path: Path,
    *,
    root: Path | None = None,
    course: str | None = None,
    source_type: str | None = None,
    provenance: dict[str, Any] | None = None,
    uri: str | None = None,
    raw_hash: str | None = None,
) -> SourceDoc:
    """Identity + hash without parsing — for the unchanged fast path of expensive formats."""
    st = source_type_for(path, source_type) or "text"
    prov = provenance or provenance_from_path(path, root, course=course)
    meta = {k: v for k, v in prov.items() if k not in ("course", "section", "lecture", "title")}
    return SourceDoc(
        title=str(prov.get("title") or prov["lecture"]),
        uri=uri or path.resolve().as_posix(),
        source_type=st,
        blocks=[],
        content_hash=raw_hash or content_hash(path.read_bytes()),
        course=prov["course"],
        section=prov["section"],
        lecture=prov["lecture"],
        meta=meta,
    )


def _links_blocks(obj: Any) -> list[Block]:
    """Udemy `external-links.json`-style lists → one block of `title — url` lines."""
    if isinstance(obj, dict):
        for key in ("links", "resources", "items"):
            if isinstance(obj.get(key), list):
                obj = obj[key]
                break
    if not isinstance(obj, list):
        raise SkipFile("json: not a transcript or a links list")
    if not obj:
        raise SkipFile("json: empty list")
    lines: list[str] = []
    for it in obj:
        if isinstance(it, dict) and any(k in it for k in ("url", "href", "link")):
            url = str(it.get("url") or it.get("href") or it.get("link"))
            title = str(it.get("title") or it.get("name") or it.get("label") or "").strip()
            lines.append(f"{title} — {url}" if title else url)
        elif isinstance(it, str) and it.startswith(("http://", "https://")):
            lines.append(it)
    if not lines:
        raise SkipFile("json: not a transcript or a links list (a dataset?)")
    return [Block(text="Links:\n" + "\n".join(lines), kind="prose", heading="Links")]


def load_file(
    path: Path,
    *,
    root: Path | None = None,
    course: str | None = None,
    source_type: str | None = None,
    trust_front_matter: bool = False,
    provenance: dict[str, Any] | None = None,
    uri: str | None = None,
    transcriber: Transcriber | None = None,
    image_reader: ImageReader | None = None,
    language: str | None = None,
    transcript_cache: Path | None = None,
    raw_hash: str | None = None,
    stt_hint: str = DEFAULT_STT_HINT,
    vision_hint: str = DEFAULT_VISION_HINT,
    vision_cache: Path | None = None,
    use_cache: bool = True,
) -> SourceDoc:
    """Raises `ValueError` for unsupported suffixes, `SkipFile` for recognised-but-empty files,
    `PdfSupportMissing` / `SttSupportMissing` / `VisionSupportMissing` for optional runtimes and
    `RuntimeError` for a missing external converter. Front matter (`uri`, `course`, `source_type`, …)
    is data from the file: it is used only when the caller says the file is owner-authored
    (`trust_front_matter`), never for course exports — otherwise a file could take over another
    document's identity. `provenance`/`uri` override the path-derived values (archive members)."""
    st = source_type_for(path, source_type)
    if st is None:
        hint = KNOWN_UNSUPPORTED.get(path.suffix.lower())
        raise ValueError(f"unsupported file type: {path.suffix}" + (f" ({hint})" if hint else ""))
    suffix = path.suffix.lower()
    prov = provenance or provenance_from_path(path, root, course=course)
    meta = {k: v for k, v in prov.items() if k not in ("course", "section", "lecture", "title")}
    default_title = str(prov.get("title") or prov["lecture"])
    uri = uri or path.resolve().as_posix()
    if suffix in MEDIA_SUFFIXES or suffix in IMAGE_SUFFIXES:
        raw_bytes = b""  # never loaded into memory: the runtimes read the file themselves
        raw_hash = raw_hash or file_hash(path)
    else:
        raw_bytes = path.read_bytes()
        raw_hash = raw_hash or content_hash(raw_bytes)
    title: str | None = None
    blocks: list[Block]

    def done(blocks: list[Block], *, source_type: str = st, title: str | None = None) -> SourceDoc:
        return SourceDoc(
            title=title or default_title,
            uri=uri,
            source_type=source_type,
            blocks=blocks,
            content_hash=raw_hash,
            course=prov["course"],
            section=prov["section"],
            lecture=prov["lecture"],
            meta=meta,
        )

    # -- media & images (registry models)
    if suffix in MEDIA_SUFFIXES:
        with tempfile.TemporaryDirectory(prefix="audhs-media-") as td:
            res = transcribe_media(
                path,
                transcriber,
                content_hash=raw_hash,
                cache_dir=transcript_cache,
                workdir=Path(td),
                language=language,
                hint=stt_hint,
                use_cache=use_cache,
            )
        meta["transcription"] = {
            "registry_id": res.registry_id,
            "model": res.model,
            "language": res.language,
            "duration_s": round(res.duration_s, 1),
            "latency_ms": res.latency_ms,
            "decoder": res.decoder,
            "source_format": res.source_format,
            "cached": res.cached,
        }
        return done(transcript_to_blocks(res))
    if suffix in IMAGE_SUFFIXES:
        with tempfile.TemporaryDirectory(prefix="audhs-image-") as td:
            blocks, vmeta = read_image(
                path,
                image_reader,
                workdir=Path(td),
                hint=vision_hint,
                cache_dir=vision_cache,
                use_cache=use_cache,
            )
        meta.update(vmeta)
        return done(blocks)  # empty blocks + meta.vision.empty: the service logs, then skips

    # -- binary containers
    if suffix in OFFICE_SUFFIXES:
        title, blocks = office_blocks(raw_bytes, suffix)
        return done(blocks, title=title)
    if suffix in LEGACY_OFFICE:
        with tempfile.TemporaryDirectory(prefix="audhs-office-") as td:
            converted = convert_legacy_office(path, Path(td))
            if converted.suffix.lower() in OFFICE_SUFFIXES:
                title, blocks = office_blocks(converted.read_bytes(), converted.suffix.lower())
            else:
                blocks = structured_blocks(
                    strip_invisible(converted.read_text(encoding="utf-8", errors="replace"))
                )
        return done(blocks, title=title)
    if suffix == ".epub":
        title, blocks = epub_blocks(raw_bytes)
        return done(blocks, title=title)
    if suffix == ".pdf" or st == "slides" and suffix == ".pdf":
        return done(pdf_blocks(raw_bytes, kind="slide" if st == "slides" else "prose"))

    # -- text formats
    if len(raw_bytes) > MAX_TEXT_BYTES:
        raise ValueError(f"text file too large ({len(raw_bytes) // 1_000_000} MB)")
    text = strip_invisible(raw_bytes.decode("utf-8", "replace"))
    if st == "markdown":
        md = parse_markdown(text)
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
    if st == "udemy_caption":
        return done(caption_blocks(text))
    if suffix in TRANSCRIPT_SUFFIXES or suffix == ".xml":
        cues = transcript_cues(text, suffix)
        if cues is None:
            raise ValueError("xml: not a TTML/DFXP transcript")
        return done(transcript_blocks(cues), source_type=source_type or "transcript")
    if st == "notebook":
        return done(notebook_blocks(text))
    if suffix == ".json":
        cues = transcript_cues(text, suffix)
        if cues:
            return done(transcript_blocks(cues), source_type=source_type or "transcript")
        try:
            blocks = _links_blocks(json.loads(text))
        except json.JSONDecodeError as e:
            raise ValueError(f"json: {e.msg}") from e
        meta["reference_only"] = True  # a list of links references material; it is not material
        return done(blocks)
    if suffix in (".tsv", ".csv"):
        cues = transcript_cues(text, suffix)
        if cues:
            return done(transcript_blocks(cues), source_type=source_type or "transcript")
        return done(_table_blocks(text, suffix))
    if suffix == ".rtf":
        return done(rtf_blocks(text))
    if suffix == ".tex":
        title, blocks = latex_blocks(text)
        return done(blocks, title=title)
    if st == "html":
        title, blocks = html_blocks(text)
        return done(blocks, title=title)
    if st == "code":
        lang = language_for(path.name)
        if lang is None:
            raise SkipFile("lockfile")
        return done(code_blocks(text, lang, filename=path.name))
    # plain / structured text: a `.txt` may be a transcript
    if suffix in (".txt", ".text"):
        cues = transcript_cues(text, suffix)
        if cues:
            return done(transcript_blocks(cues), source_type=source_type or "transcript")
    if suffix in STRUCTURED_SUFFIXES:
        return done(structured_blocks(text))
    return done([Block(text=p.strip()) for p in re.split(r"\n\s*\n", text) if p.strip()])


def _table_blocks(text: str, suffix: str) -> list[Block]:
    import csv
    import io

    rows = list(csv.reader(io.StringIO(text), delimiter="\t" if suffix == ".tsv" else ","))
    lines = [
        "| " + " | ".join(c.strip() for c in r) + " |"
        for r in rows[:200]
        if any(c.strip() for c in r)
    ]
    if not lines:
        raise SkipFile("empty table")
    if len(rows) > 200:
        lines.append("| … |")
    return [Block(text="\n".join(lines), kind="table")]


def _walk_skip(rel_parts: tuple[str, ...]) -> bool:
    return any(p.startswith(".") for p in rel_parts[:-1]) or any(
        p in SKIP_DIRS for p in rel_parts[:-1]
    )


def iter_source_files(src: Path) -> list[Path]:
    """Every ingestible file under `src` (or `src` itself): known suffixes, code filenames, archives
    and known-unsupported types (so they show up as skipped). Hidden/build folders, Udemy metadata,
    secret-looking names and lockfiles are left out. Several caption languages per lecture collapse
    to one (English preferred)."""
    if src.is_file():
        return [src]
    files: list[Path] = []
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src).parts
        if _walk_skip(rel) or p.name.lower() in IGNORED_NAMES or p.name.lower() in LOCKFILES:
            continue
        if should_skip_relpath("/".join(rel)) == "possible secret file":
            continue
        if p.name.startswith("."):
            continue
        suffix = p.suffix.lower()
        if (
            suffix in SUFFIX_TYPES
            or suffix in KNOWN_UNSUPPORTED
            or is_archive(p)
            or language_for(p.name) is not None
        ):
            files.append(p)
    # Udemy exports often ship several caption languages: keep one per lecture (prefer English).
    seen: dict[tuple[Path, str], Path] = {}
    for p in files:
        key = (p.parent, clean_stem(p) + p.suffix.lower())
        if key not in seen or (".en" in p.stem.lower() and ".en" not in seen[key].stem.lower()):
            seen[key] = p
    return sorted(seen.values())
