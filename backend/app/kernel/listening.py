"""Guided listening (P7): a language block built from an *already ingested* caption/transcript
document whose media file sits next to it under the ingest roots. No parallel lesson database:
sections are the document's timed chunks, tasks are `assessment` rows on the per-language listening
node, answers/evidence/scheduling go through the ordinary grader (FSRS ≠ competency, ADR-0004), and
progress is derived from attempts. Playing a clip is exposure, logged as `listened`, never evidence.
"""

from __future__ import annotations

import asyncio
import re
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Assessment,
    AssessmentAttempt,
    Chunk,
    ChunkProvenance,
    Document,
    DocumentVersion,
    SkillNode,
)
from app.kernel.curriculum import STOP_WORDS, WORD_RE, open_target
from app.knowledge.ingest.loaders import _LANG_SUFFIX, SUFFIX_TYPES, clean_stem

MAX_CLIP_S = 240.0  # one bounded clip; longer sections are skipped, never auto-played whole
MIN_CLIP_S = 2.0
MAX_MEDIA_BYTES = 2 * 1024**3
TIMED_SOURCE_TYPES = ("udemy_caption", "transcript", "audio", "video")
MEDIA_SUFFIXES = tuple(sfx for sfx, kind in SUFFIX_TYPES.items() if kind in ("audio", "video"))
LISTENING_KIND = "listening"


def listening_slug(lang: str) -> str:
    return f"lang-{lang.lower()}-listening"


async def listening_node(db: AsyncSession, lang: str, *, commit: bool = True) -> SkillNode:
    """Get-or-create the per-language listening node (domain language, never a tutor lesson)."""
    slug = listening_slug(lang)
    node = (await db.execute(select(SkillNode).where(SkillNode.slug == slug))).scalar_one_or_none()
    if node is None:
        node = SkillNode(
            slug=slug,
            domain="language",
            title=f"Listening ({lang.upper()})",
            description="Guided listening: bounded clips from your own course audio with one "
            "comprehension task each.",
            success_criteria_json=["Recall a word or fact from a short clip you have just heard."],
            assessment_requirements_json={
                "teachable": False,
                "kind": LISTENING_KIND,
                "dimensions": ["recall"],
            },
            example_applications_json=[],
        )
        db.add(node)
        await (db.commit() if commit else db.flush())
    return node


# ----------------------------------------------------------------------------- media next to text
def media_for(uri: str, roots: list[Path]) -> Path | None:
    """The playable file for a document: the document itself when it is audio/video, else a media
    file with the same (language-stripped) stem next to the caption. Only plain files under the
    ingest roots are ever served."""
    if not uri or "!/" in uri or uri.startswith(("http://", "https://")):
        return None
    p = Path(uri)
    if p.suffix.lower() in MEDIA_SUFFIXES:
        return open_target(uri, roots)
    stem = clean_stem(p)
    parent = p.parent
    try:
        parent_r = parent.resolve()
    except OSError:
        return None
    if not any(parent_r == r or r in parent_r.parents for r in roots):
        return None  # never list a directory outside the ingest roots
    try:
        candidates = sorted(
            c
            for c in parent.iterdir()
            if c.is_file() and c.suffix.lower() in MEDIA_SUFFIXES and clean_stem(c) == stem
        )
    except OSError:
        return None
    for c in candidates:
        ok = open_target(str(c), roots)
        if ok is not None:
            return ok
    return None


def media_duration_s(path: Path) -> float | None:
    """Duration when it can be read without extra dependencies (WAV); None otherwise."""
    if path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as w:
            rate = w.getframerate()
            return w.getnframes() / rate if rate else None
    except (wave.Error, OSError, EOFError):
        return None


# ----------------------------------------------------------------------------- sections
@dataclass
class Section:
    index: int
    chunk_id: str
    t_start: float
    t_end: float
    text: str
    done: bool = False
    attempts: int = 0


@dataclass
class Lesson:
    document_id: str
    title: str
    course: str | None
    section: str | None
    lecture: str | None
    language: str | None
    media_path: Path | None
    duration_s: float | None
    sections: list[Section] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)

    @property
    def next_index(self) -> int | None:
        for s in self.sections:
            if not s.done:
                return s.index
        return None


def language_of(uri: str) -> str | None:
    """Language from the caption stem (`lecture.en.vtt`, `talk.de-DE`), same whitelist as ingest."""
    stem = Path(uri).stem  # "lecture.en"
    m = _LANG_SUFFIX.search(stem)
    if not m:
        return None
    lang = m.group(1).lower()
    return None if lang == "auto" else lang.split("-")[0]


def bound_sections(
    rows: list[tuple[str, float | None, float | None, str]], duration_s: float | None
) -> tuple[list[Section], list[dict[str, Any]]]:
    """Timed chunks → bounded, non-overlapping clips. Malformed (missing/negative/zero-length),
    over-long, or out-of-media cues are skipped with a reason; an overlap is clipped to the
    previous clip's end. Deterministic, no I/O."""
    out: list[Section] = []
    skipped: list[dict[str, Any]] = []
    prev_end = 0.0
    for chunk_id, t0, t1, text in rows:
        if t0 is None or t1 is None:
            skipped.append({"chunk_id": chunk_id, "reason": "no timestamps"})
            continue
        start, end = float(t0), float(t1)
        if start < 0 or end <= start:
            skipped.append({"chunk_id": chunk_id, "reason": "malformed timestamps"})
            continue
        if start < prev_end:  # overlapping cue: keep the clip inside its own span
            start = prev_end
            if end - start < MIN_CLIP_S:
                skipped.append({"chunk_id": chunk_id, "reason": "overlaps the previous clip"})
                continue
        if end - start > MAX_CLIP_S:  # judged on the cue itself, before clipping to the audio
            skipped.append(
                {"chunk_id": chunk_id, "reason": f"clip longer than {int(MAX_CLIP_S)} s"}
            )
            continue
        if duration_s is not None and start >= duration_s - 0.5:
            skipped.append({"chunk_id": chunk_id, "reason": "beyond the end of the audio"})
            continue
        if duration_s is not None:
            end = min(end, duration_s)
        if end - start < MIN_CLIP_S or not text.strip():
            reason = (
                "beyond the end of the audio"
                if duration_s is not None and end == duration_s
                else "too short or empty"
            )
            skipped.append({"chunk_id": chunk_id, "reason": reason})
            continue
        out.append(
            Section(index=len(out), chunk_id=chunk_id, t_start=start, t_end=end, text=text.strip())
        )
        prev_end = end
    return out, skipped


_STOP_DE = frozenset(
    "welche welcher welches werden wurden können könnte müssen sollte sollen haben hatten "
    "dieser dieses diesen einige andere immer nichts alles zwischen während".split()
)


def _body(text: str) -> str:
    return text.split("\n", 1)[1] if "\n" in text else text


async def _timed_documents(db: AsyncSession) -> list[tuple[Document, int]]:
    latest = (
        select(DocumentVersion.document_id, func.max(DocumentVersion.version).label("v"))
        .group_by(DocumentVersion.document_id)
        .subquery()
    )
    stmt = (
        select(Document, func.count(Chunk.id))
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .join(
            latest,
            (latest.c.document_id == DocumentVersion.document_id)
            & (latest.c.v == DocumentVersion.version),
        )
        .join(Chunk, Chunk.document_version_id == DocumentVersion.id)
        .where(
            Document.source_type.in_(TIMED_SOURCE_TYPES),
            Chunk.t_start.is_not(None),
            Chunk.duplicate_of.is_(None),
        )
        .group_by(Document.id)
        .order_by(Document.course, Document.section, Document.lecture, Document.title)
    )
    return [(d, int(n)) for d, n in (await db.execute(stmt)).all()]


async def _done_chunks(db: AsyncSession, learner_id: str) -> dict[str, int]:
    """chunk_id → attempts by this learner on listening tasks."""
    stmt = (
        select(Assessment.item_json, func.count(AssessmentAttempt.id))
        .join(AssessmentAttempt, AssessmentAttempt.assessment_id == Assessment.id)
        .join(SkillNode, SkillNode.id == Assessment.skill_id)
        .where(AssessmentAttempt.learner_id == learner_id, SkillNode.slug.like("lang-%-listening"))
        .group_by(Assessment.id)
    )
    out: dict[str, int] = {}
    for item, n in (await db.execute(stmt)).all():
        lst = (item or {}).get("listening") or {}
        cid = str(lst.get("chunk_id") or "")
        if cid:
            out[cid] = out.get(cid, 0) + int(n)
    return out


async def lessons(db: AsyncSession, learner_id: str, roots: list[Path]) -> list[dict[str, Any]]:
    """Every ingested document with timestamps; says whether its audio is available."""
    done = await _done_chunks(db, learner_id)
    out = []
    for doc, n in await _timed_documents(db):
        lesson = await load_lesson(db, learner_id, doc.id, roots, done=done)
        out.append(
            {
                "document_id": doc.id,
                "title": doc.title,
                "course": doc.course,
                "section": doc.section,
                "lecture": doc.lecture,
                "language": language_of(doc.uri),
                "sections": len(lesson.sections) if lesson else 0,
                "done": sum(1 for s in lesson.sections if s.done) if lesson else 0,
                "next_index": lesson.next_index if lesson else None,
                "media_available": bool(lesson and lesson.media_path is not None),
                "duration_s": lesson.duration_s if lesson else None,
                "timed_chunks": n,
            }
        )
    return out


async def load_lesson(
    db: AsyncSession,
    learner_id: str,
    document_id: str,
    roots: list[Path],
    *,
    done: dict[str, int] | None = None,
) -> Lesson | None:
    doc = await db.get(Document, document_id)
    if doc is None:
        return None
    latest = (
        await db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is None:
        return None
    rows = [
        (c.id, c.t_start, c.t_end, _body(c.text))
        for c in (
            await db.execute(
                select(Chunk)
                .where(Chunk.document_version_id == latest.id, Chunk.duplicate_of.is_(None))
                .order_by(Chunk.ordinal)
            )
        ).scalars()
    ]
    media = await asyncio.to_thread(media_for, doc.uri, roots)
    duration = (await asyncio.to_thread(media_duration_s, media)) if media else None
    sections, skipped = bound_sections(rows, duration)
    # a clip whose transcript offers no task would be a dead end (P7 review): skip it up front
    usable: list[Section] = []
    for sec in sections:
        if deterministic_task(sec) is None:
            skipped.append({"chunk_id": sec.chunk_id, "reason": "transcript offers no task"})
        else:
            sec.index = len(usable)
            usable.append(sec)
    sections = usable
    done = done if done is not None else await _done_chunks(db, learner_id)
    for s in sections:
        s.attempts = done.get(s.chunk_id, 0)
        s.done = s.attempts > 0
    return Lesson(
        document_id=doc.id,
        title=doc.title,
        course=doc.course,
        section=doc.section,
        lecture=doc.lecture,
        language=language_of(doc.uri),
        media_path=media,
        duration_s=duration,
        sections=sections,
        skipped=skipped,
    )


# ----------------------------------------------------------------------------- tasks
def deterministic_task(section: Section) -> dict[str, Any] | None:
    """A cloze cut from the clip's own transcript: a content word (≥ 6 letters, not a stop word)
    in a sentence of usable length. Nothing invented. None when the text offers nothing."""
    sents = [" ".join(s.split()) for s in re.split(r"(?<=[.!?])\s+", section.text)]
    for sent in sents:
        if not 40 <= len(sent) <= 220:
            continue
        words = [
            m
            for m in WORD_RE.finditer(sent)
            if len(m.group(0)) >= 6
            and m.group(0).isalpha()
            and m.group(0).lower() not in STOP_WORDS
            and m.group(0).lower() not in _STOP_DE
            and m.start() > 0  # never the sentence opener
        ]
        if not words:
            continue
        target = max(words, key=lambda m: len(m.group(0)))
        return {
            "kind": "cloze",
            "item": {
                "text": sent[: target.start()] + "____" + sent[target.end() :],
                "answers": [target.group(0)],
            },
        }
    return None


async def existing_task(db: AsyncSession, node_id: str, chunk_id: str) -> Assessment | None:
    stmt = (
        select(Assessment)
        .where(
            Assessment.skill_id == node_id,
            Assessment.item_json["listening"]["chunk_id"].as_string() == chunk_id,
        )
        .order_by(Assessment.id)
    )
    return (await db.execute(stmt)).scalars().first()


async def validate_task(db: AsyncSession, assessment_id: str, *, validated: bool) -> Assessment:
    """The review path for model-proposed questions: the learner marks a question as checked
    (full weight from then on) or leaves it unvalidated (half weight in the grader)."""
    a = await db.get(Assessment, assessment_id)
    if a is None or not (a.item_json or {}).get("listening"):
        raise KeyError("no such listening task")
    item = dict(a.item_json)
    item["listening"] = {**item["listening"], "validated": validated}
    a.item_json = item
    await db.commit()
    return a


async def store_task(
    db: AsyncSession,
    node: SkillNode,
    lesson: Lesson,
    section: Section,
    *,
    kind: str,
    item: dict[str, Any],
    origin: str,
    model_call_id: str | None,
) -> Assessment:
    """One assessment per clip. `item.listening` keeps the provenance (document, chunk, clip
    bounds); the transcript is not stored in the item (the chunk is the source of truth)."""
    payload = dict(item)
    payload["listening"] = {
        "document_id": lesson.document_id,
        "chunk_id": section.chunk_id,
        "t_start": section.t_start,
        "t_end": section.t_end,
        "origin": origin,
        "model_call_id": model_call_id,
        "validated": origin == "deterministic",
    }
    a = Assessment(skill_id=node.id, kind=kind, item_json=payload, rubric_id=None)
    db.add(a)
    await db.commit()
    return a


async def provenance_citation(
    db: AsyncSession, chunk_id: str, t_start: float | None = None
) -> str | None:
    prov = (
        await db.execute(select(ChunkProvenance).where(ChunkProvenance.chunk_id == chunk_id))
    ).scalar_one_or_none()
    if prov is None:
        return None
    parts = [p for p in (prov.course, prov.section, prov.lecture) if p]
    time = f" @{int(t_start) // 60:02d}:{int(t_start) % 60:02d}" if t_start is not None else ""
    return "[" + " › ".join(parts) + time + "]"
