"""Course → curriculum workflow (P4 `curriculum-drafts`).

Ingested material is *searchable*; it becomes *learnable* only through a reviewed, published
curriculum: skill nodes with prerequisites, one LearningObject per skill (concept, goal, examples,
exercises, success criteria, sources = chunk ids), and assessments with rubrics. This module is
deterministic: a draft is proposed from the documents of one course section (one skill per lecture,
prerequisites in lecture order, cloze candidates cut from the source text — never invented),
validated (cycles, unknown prerequisites, missing objects/assessments, broken provenance), edited by
the learner and published explicitly. Publishing writes a *new* LearningObject version and new
assessment rows; nothing that produced historical evidence is overwritten. A model may draft the
same payload through the orchestrator (`origin="model"`); it is untrusted until reviewed, exactly
like this deterministic draft."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow_iso
from app.db.models import (
    Assessment,
    AssessmentRubric,
    Chunk,
    ChunkProvenance,
    ContentReport,
    CourseSource,
    CurriculumDraft,
    Document,
    DocumentVersion,
    LearningObject,
    SkillEdge,
    SkillNode,
)
from app.knowledge.ingest.loaders import clean_stem, split_number
from app.knowledge.ingest.udemy_manifest import parse_lecture_dir, parse_section_dir

STATUSES = ("draft", "published", "rejected")
MATERIAL_STATUSES = ("imported", "searchable", "draft", "published")
SOURCE_ROLES = ("primary", "supplemental", "excluded")
MAX_SKILLS_PER_DRAFT = 30
MAX_CLOZE_PER_SKILL = 3
MAX_SOURCES_PER_OBJECT = 8  # passages cited per learning object (the first N of a lecture)
_SENT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-zÄÖÜäöüß][\w\-]{3,}")


@dataclass
class Problem:
    level: str  # error | warning | info (a note about what the draft is built on)
    where: str  # skill slug or "draft"
    message: str


@dataclass
class SectionMaterial:
    course: str
    section: str | None
    lectures: list[dict[str, Any]] = field(default_factory=list)  # {lecture, document_id, chunks}
    # documents of the section that were *not* used, by role — so a draft can say what it left out
    left_out: list[dict[str, Any]] = field(default_factory=list)  # {document_id, title, role, …}

    @property
    def unique_chunks(self) -> int:
        """Coverage: latest-version, non-duplicate passages behind the draft."""
        return sum(len(lec["chunks"]) for lec in self.lectures)


# ----------------------------------------------------------------------------- source roles
def suggest_role(doc: Document, *, section_has_plain_documents: bool = True) -> tuple[str, str]:
    """Deterministic, literal suggestion of what a document is for its course. Only the owner's
    decision (a `course_source` row) overrides it; the suggestion never changes provenance.
    `section_has_plain_documents`: whether the document's section also holds material that is
    not an archive member — when an archive is a section's *only* material it is the lessons."""
    uri = (doc.uri or "").lower()
    name = uri.rsplit("/", 1)[-1]
    if name.endswith("external-links.json") or "external-links" in name:
        return "supplemental", "a list of links: references, not teaching material"
    if "!/" in uri:
        if not section_has_plain_documents:
            return "primary", "member of the archive that is this section's only material"
        return "supplemental", "member of a bundled archive (repository, software docs, notebook)"
    if doc.source_type in ("code", "notebook") and path_numbers(doc.uri)[1] is None:
        # a numbered notebook is a lecture slot the instructor filled; an unnumbered one next to
        # the lectures is community/bonus material until the owner says otherwise
        return "supplemental", "unnumbered code or notebook: reference material, not a lecture"
    return "primary", "no rule matched: treated as lecture material until you change it"


async def source_roles(db: AsyncSession, course: str) -> dict[str, dict[str, Any]]:
    """Effective role per document id of a course: the owner's decision when there is one,
    otherwise the suggestion (marked `decided_by: suggested`)."""
    decided = {
        r.document_id: r
        for r in (await db.execute(select(CourseSource).where(CourseSource.course == course)))
        .scalars()
        .all()
    }
    docs = (await db.execute(select(Document).where(Document.course == course))).scalars().all()
    # a section has "plain material" when a non-archive document there is itself suggested
    # primary (a lone external-links.json next to a resources.zip does not count)
    plain_sections = {
        d.section
        for d in docs
        if "!/" not in (d.uri or "")
        and suggest_role(d, section_has_plain_documents=True)[0] == "primary"
    }
    out: dict[str, dict[str, Any]] = {}
    for doc in docs:
        row = decided.get(doc.id)
        if row is not None:
            out[doc.id] = {"role": row.role, "reason": row.reason, "decided_by": "owner"}
        else:
            role, why = suggest_role(doc, section_has_plain_documents=doc.section in plain_sections)
            out[doc.id] = {"role": role, "reason": why, "decided_by": "suggested"}
    return out


async def course_sources(db: AsyncSession, course: str) -> list[dict[str, Any]]:
    """Every document of a course with its effective role, in section/lecture order, plus the
    number of unique latest-version passages it contributes."""
    roles = await source_roles(db, course)
    latest = (
        select(DocumentVersion.document_id, func.max(DocumentVersion.version).label("v"))
        .group_by(DocumentVersion.document_id)
        .subquery()
    )
    counts = {
        str(doc_id): int(n)
        for doc_id, n in (
            await db.execute(
                select(DocumentVersion.document_id, func.count(Chunk.id))
                .join(
                    latest,
                    (latest.c.document_id == DocumentVersion.document_id)
                    & (latest.c.v == DocumentVersion.version),
                )
                .join(Chunk, Chunk.document_version_id == DocumentVersion.id)
                .where(Chunk.duplicate_of.is_(None))
                .group_by(DocumentVersion.document_id)
            )
        ).all()
    }
    docs = (await db.execute(select(Document).where(Document.course == course))).scalars().all()
    out = []
    for doc in docs:
        sec_no, lec_no = path_numbers(doc.uri)
        out.append(
            {
                "document_id": doc.id,
                "title": doc.title,
                "section": doc.section,
                "lecture": doc.lecture,
                "source_type": doc.source_type,
                "uri": doc.uri,
                "chunks": counts.get(doc.id, 0),
                "section_no": sec_no,
                "lecture_no": lec_no,
                **roles[doc.id],
            }
        )
    out.sort(
        key=lambda d: (
            _order_key(d["section_no"], d["section"]),
            _order_key(d["lecture_no"], str(d["lecture"] or d["title"])),
        )
    )
    return out


async def set_source_role(
    db: AsyncSession, course: str, document_id: str, role: str, reason: str = ""
) -> dict[str, Any]:
    """The owner's decision for one document (upsert). Never touches the document itself."""
    if role not in SOURCE_ROLES:
        raise ValueError(f"role must be one of {SOURCE_ROLES}")
    doc = await db.get(Document, document_id)
    if doc is None or doc.course != course:
        raise KeyError(document_id)
    row = (
        await db.execute(select(CourseSource).where(CourseSource.document_id == document_id))
    ).scalar_one_or_none()
    if row is None:
        row = CourseSource(course=course, document_id=document_id, role=role, reason=reason)
        db.add(row)
    else:
        row.role, row.reason, row.decided_at = role, reason, utcnow_iso()
    await db.commit()
    return {"role": role, "reason": reason, "decided_by": "owner"}


async def reset_source_role(db: AsyncSession, course: str, document_id: str) -> dict[str, Any]:
    """Drop the owner's decision: the suggestion applies again."""
    doc = await db.get(Document, document_id)
    if doc is None or doc.course != course:
        raise KeyError(document_id)
    await db.execute(
        delete(CourseSource).where(
            CourseSource.document_id == document_id, CourseSource.course == course
        )
    )
    await db.commit()
    return (await source_roles(db, course))[doc.id]


async def set_archive_role(
    db: AsyncSession, course: str, archive: str, role: str, reason: str = ""
) -> int:
    """One decision for every member of an archive (`archive` = the archive file name or its full
    uri prefix): a bundle of 100 files must not need 100 clicks. Returns the number of documents."""
    if role not in SOURCE_ROLES:
        raise ValueError(f"role must be one of {SOURCE_ROLES}")
    docs = (await db.execute(select(Document).where(Document.course == course))).scalars().all()
    members = [
        d
        for d in docs
        if "!/" in (d.uri or "")
        and (d.uri.split("!/", 1)[0] == archive or d.uri.split("!/", 1)[0].endswith("/" + archive))
    ]
    for d in members:
        await set_source_role(db, course, d.id, role, reason)
    return len(members)


def slugify(text: str, *, prefix: str = "") -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "skill"
    return f"{prefix}{base}" if prefix else base


def draft_prefix(course: str, section: str | None) -> str:
    """Slug prefix = course + section, so "Introduction" in two sections never collides."""
    prefix = slugify(course)[:20]
    if section:
        prefix += "-" + slugify(section)[:16]
    return prefix + "-"


def lecture_slugs(mat: SectionMaterial) -> list[str]:
    """One slug per lecture (draft order), unique within the draft (`-2`, `-3` on repeats)."""
    prefix = draft_prefix(mat.course, mat.section)
    seen: dict[str, int] = {}
    out: list[str] = []
    for lec in mat.lectures[:MAX_SKILLS_PER_DRAFT]:
        slug = slugify(str(lec["lecture"]), prefix=prefix)
        n = seen.get(slug, 0)
        seen[slug] = n + 1
        out.append(slug if n == 0 else f"{slug}-{n + 1}")
    return out


def path_numbers(uri: str) -> tuple[int | None, int | None]:
    """(section_no, lecture_no) re-derived from the file path `<NN - Section>/<NNN - Lecture>.ext`.
    Ingest strips the numbers from the stored labels (they only live in transient meta), so the
    path is the durable place to read them from; archive members use the member path."""
    if not uri or uri.startswith(("http://", "https://")):
        return None, None
    outer, member = (uri.split("!/", 1) + [""])[:2] if "!/" in uri else (uri, "")
    p = Path(member or outer)
    # the resources export files assets under `Section N - title/Lecture a-b - M. title/`; the
    # plain layout numbers files `NN - Section/MMM - Lecture.ext`; both are read from the *outer*
    # path (an archive's member path rarely carries the course numbering)
    op = Path(outer)
    lecture_dir = parse_lecture_dir(op.parent.name)
    if lecture_dir is not None:
        lecture_no = lecture_dir[0]
        section_dir = op.parent.parent.name
    else:
        lecture_no, _ = split_number(clean_stem(p))
        section_dir = op.parent.name if not member else (op.parent.name)
    section_dir_parsed = parse_section_dir(section_dir)
    section_no = section_dir_parsed[0] if section_dir_parsed else split_number(section_dir)[0]
    if member and lecture_dir is None:
        # an archive member inside a numbered lecture file (`003 - starter.zip!/a.py`): the
        # archive's own number is the lecture slot
        archive_no, _ = split_number(clean_stem(op))
        lecture_no = lecture_no if lecture_no is not None else archive_no
    return section_no, lecture_no


def _order_key(no: int | None, label: str | None) -> tuple[int, int, str]:
    return (no is None, no or 0, (label or "").lower())


# ----------------------------------------------------------------------------- material status
async def material_status(db: AsyncSession, learner_id: str) -> list[dict[str, Any]]:
    """Per course: imported documents, searchable chunks, the learner's drafts, published skills."""
    docs = (
        await db.execute(
            select(Document.course, func.count(Document.id))
            .where(Document.course.is_not(None))
            .group_by(Document.course)
        )
    ).all()
    chunks_by_course: dict[str, int] = {}
    for course, n in (
        await db.execute(
            select(ChunkProvenance.course, func.count(ChunkProvenance.id))
            .join(Chunk, Chunk.id == ChunkProvenance.chunk_id)
            .where(ChunkProvenance.course.is_not(None), Chunk.duplicate_of.is_(None))
            .group_by(ChunkProvenance.course)
        )
    ).all():
        chunks_by_course[str(course)] = int(n)
    drafts: dict[str, dict[str, int]] = {}
    for course, status, n in (
        await db.execute(
            select(CurriculumDraft.course, CurriculumDraft.status, func.count(CurriculumDraft.id))
            .where(CurriculumDraft.learner_id == learner_id)
            .group_by(CurriculumDraft.course, CurriculumDraft.status)
        )
    ).all():
        drafts.setdefault(str(course), {})[str(status)] = int(n)
    published: dict[str, int] = {}
    for course, n in (
        await db.execute(
            select(SkillNode.course, func.count(SkillNode.id))
            .where(SkillNode.course.is_not(None))
            .group_by(SkillNode.course)
        )
    ).all():
        published[str(course)] = int(n)
    out = []
    for course, n_docs in docs:
        c = str(course)
        d = drafts.get(c, {})
        status = (
            "published"
            if published.get(c)
            else "draft"
            if d.get("draft")
            else "searchable"
            if chunks_by_course.get(c)
            else "imported"
        )
        out.append(
            {
                "course": c,
                "documents": int(n_docs),
                "chunks": chunks_by_course.get(c, 0),
                "drafts": d.get("draft", 0),
                "published_skills": published.get(c, 0),
                "status": status,
            }
        )
    for c, n in published.items():  # published from a seed (no documents)
        if not any(o["course"] == c for o in out):
            out.append(
                {
                    "course": c,
                    "documents": 0,
                    "chunks": 0,
                    "drafts": 0,
                    "published_skills": n,
                    "status": "published",
                }
            )
    return sorted(out, key=lambda o: o["course"])


async def sections_of(db: AsyncSession, course: str) -> list[dict[str, Any]]:
    """Sections in course order (folder number, then label); documents per section."""
    rows = (
        await db.execute(select(Document.section, Document.uri).where(Document.course == course))
    ).all()
    agg: dict[str | None, dict[str, Any]] = {}
    for section, uri in rows:
        entry = agg.setdefault(section, {"section": section, "documents": 0, "no": None})
        entry["documents"] += 1
        if section is None:
            continue  # loose root files have no place in the course order: they sort last
        no, _ = path_numbers(str(uri or ""))
        if no is not None and (entry["no"] is None or no < entry["no"]):
            entry["no"] = no
    for e in agg.values():
        if e["no"] is None and e["section"]:
            e["no"] = label_number(str(e["section"]))
    ordered = sorted(agg.values(), key=lambda e: _order_key(e["no"], e["section"]))
    return [{"section": e["section"], "documents": e["documents"]} for e in ordered]


_LABEL_NO = re.compile(
    r"^(?:chapter|kapitel|section|abschnitt|part|teil|module|modul|week|woche|unit|lesson|lektion)"
    r"\s*(\d+)\b",
    re.I,
)


def label_number(label: str) -> int | None:
    """A section whose folder carries no number may still say where it belongs in its own label
    ("chapter 2 Transformers Architecture" from an instructor repository next to the numbered
    export). Literal prefixes only; anything else stays unnumbered and sorts last."""
    m = _LABEL_NO.match(label.strip())
    return int(m.group(1)) if m else None


async def section_material(db: AsyncSession, course: str, section: str | None) -> SectionMaterial:
    """Latest-version unique chunks of every **primary** document (= lecture) in the section, in
    order. Supplemental and excluded documents are listed in `left_out` and never contribute a
    skill, a source passage or a cloze; duplicates (`Chunk.duplicate_of`) never inflate coverage."""
    roles = await source_roles(db, course)
    latest = (
        select(DocumentVersion.document_id, func.max(DocumentVersion.version).label("v"))
        .group_by(DocumentVersion.document_id)
        .subquery()
    )
    stmt = (
        select(Document, Chunk)
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .join(
            latest,
            (latest.c.document_id == DocumentVersion.document_id)
            & (latest.c.v == DocumentVersion.version),
        )
        .join(Chunk, Chunk.document_version_id == DocumentVersion.id)
        .where(Document.course == course, Chunk.duplicate_of.is_(None))
        .order_by(Chunk.ordinal)
    )
    if section is None:
        stmt = stmt.where(Document.section.is_(None))
    else:
        stmt = stmt.where(Document.section == section)
    mat = SectionMaterial(course=course, section=section)
    # one slot per *lecture*: documents filed under the same lecture label (an archive's members,
    # two notebooks of one lesson) are one lesson with all their passages, not one skill each
    by_doc: dict[str, dict[str, Any]] = {}
    slots: dict[tuple[str, str], dict[str, Any]] = {}
    seen_out: set[str] = set()
    for doc, chunk in (await db.execute(stmt)).all():
        role = roles.get(doc.id, {}).get("role", "primary")
        if role != "primary":
            if doc.id not in seen_out:
                seen_out.add(doc.id)
                mat.left_out.append(
                    {
                        "document_id": doc.id,
                        "title": doc.title,
                        "role": role,
                        "reason": roles[doc.id]["reason"],
                        "decided_by": roles[doc.id]["decided_by"],
                    }
                )
            continue
        key = ("lecture", doc.lecture) if doc.lecture else ("document", doc.id)
        entry = slots.get(key)
        if entry is None:
            entry = slots[key] = {
                "lecture": doc.lecture or doc.title,
                "document_id": doc.id,  # the first document: the slot's identity for older readers
                "title": doc.title,
                "lecture_no": path_numbers(doc.uri)[1],
                "documents": [],
                "chunks": [],
            }
        if doc.id not in by_doc:
            by_doc[doc.id] = entry
            entry["documents"].append({"document_id": doc.id, "title": doc.title, "passages": 0})
            if entry["lecture_no"] is None:
                entry["lecture_no"] = path_numbers(doc.uri)[1]
        entry["documents"][
            -1
            if entry["documents"][-1]["document_id"] == doc.id
            else next(i for i, d in enumerate(entry["documents"]) if d["document_id"] == doc.id)
        ]["passages"] += 1
        entry["chunks"].append(
            {
                "id": chunk.id,
                "text": chunk.text,
                "t_start": chunk.t_start,
                "ordinal": chunk.ordinal,
                "document_id": doc.id,
            }
        )
    # passages stay grouped per document (in the order the documents were met), then by ordinal
    for entry in slots.values():
        order = {d["document_id"]: i for i, d in enumerate(entry["documents"])}
        entry["chunks"].sort(key=lambda c: (order[c["document_id"]], c["ordinal"]))
    # lecture order = file number (001, 002, …), never the alphabetical label
    mat.lectures = sorted(
        slots.values(), key=lambda e: _order_key(e["lecture_no"], str(e["lecture"]))
    )
    # a primary document whose text is entirely a duplicate of another has no unique passages:
    # it gets no lecture slot, and it must be said rather than silently vanish
    docs_stmt = select(Document).where(Document.course == course)
    docs_stmt = (
        docs_stmt.where(Document.section.is_(None))
        if section is None
        else docs_stmt.where(Document.section == section)
    )
    for doc in (await db.execute(docs_stmt)).scalars():
        if doc.id in by_doc or doc.id in seen_out:
            continue
        if roles.get(doc.id, {}).get("role", "primary") == "primary":
            mat.left_out.append(
                {
                    "document_id": doc.id,
                    "title": doc.title,
                    "role": "primary",
                    "reason": "no unique passages: all of its text duplicates another document "
                    "of this course (or it has no text)",
                    "decided_by": roles.get(doc.id, {}).get("decided_by", "suggested"),
                }
            )
    return mat


# ----------------------------------------------------------------------------- deterministic draft
def _body(text: str) -> str:
    """Chunk text minus the `title › heading` prefix line."""
    return text.split("\n", 1)[1] if "\n" in text else text


_STOP = frozenset(
    "about after again always around because before being between could every first going "
    "having might other really right should something still their there these thing things "
    "think those through under using where which while would little people".split()
)


STOP_WORDS = _STOP
WORD_RE = _WORD


def _cloze_candidates(lecture_title: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Source-grounded cloze items: a sentence from the material that mentions the lecture topic,
    with a *content* word blanked. Nothing is invented; the answer is a word as written in the
    source. A title word is never the preferred blank — the skill title is shown above the item, so
    it would be guessable; when nothing else qualifies the item is marked `guessable` so the
    validator warns and the learner edits or replaces it."""
    terms = [w for w in _WORD.findall(lecture_title) if len(w) >= 4]
    title_terms = {t.lower() for t in terms}
    out: list[dict[str, Any]] = []
    for c in chunks:
        for sent in _SENT.split(_body(c["text"])):
            sent = " ".join(sent.split())
            if not 40 <= len(sent) <= 220:
                continue
            hit = next(
                (
                    m
                    for term in terms
                    if (m := re.search(rf"\b{re.escape(term)}\b", sent, re.IGNORECASE))
                ),
                None,
            )
            if hit is None:
                continue
            content = [
                m
                for m in _WORD.finditer(sent)
                if len(m.group(0)) >= 6
                and m.group(0).lower() not in title_terms
                and m.group(0).lower() not in _STOP
                and m.group(0).isalpha()
            ]
            target = max(content, key=lambda m: len(m.group(0))) if content else hit
            item: dict[str, Any] = {
                "kind": "cloze",
                "item": {
                    "text": sent[: target.start()] + "____" + sent[target.end() :],
                    "answers": [target.group(0)],
                },
                "source_chunk_id": c["id"],
                "auto": True,
            }
            if not content:
                item["guessable"] = True
            out.append(item)
            if len(out) >= MAX_CLOZE_PER_SKILL:
                return out
    return out


_WORD = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ_-]{4,}")


def salient_terms(texts: list[str], n: int = 8) -> list[str]:
    """The most frequent longer words of a lecture outside code fences and stop words, lowercased:
    the vocabulary a learner's explanation would naturally use. Deterministic, order by count then
    first appearance."""
    counts: dict[str, int] = {}
    first: dict[str, int] = {}
    for text in texts:
        body = re.sub(r"```.*?```", " ", _body(text), flags=re.S)
        for m in _WORD.finditer(body):
            w = m.group(0).lower().strip("_-")
            if w in _STOP or len(w) < 5:
                continue
            counts[w] = counts.get(w, 0) + 1
            first.setdefault(w, len(first))
    return sorted(counts, key=lambda w: (-counts[w], first[w]))[:n]


def rubric_from_criteria(criteria: list[str], fallback_terms: list[str]) -> list[dict[str, Any]]:
    """One rubric row per success criterion; the keywords are the criterion's own longer words
    (the deterministic level checks them, the LLM level reads the criterion text)."""
    rows: list[dict[str, Any]] = []
    for c in criteria:
        kws = [w.lower() for w in _WORD.findall(c) if w.lower() not in _STOP][:5]
        rows.append({"criterion": c.strip(), "keywords": kws or fallback_terms[:4]})
    return rows


def explain_back_item(
    slug: str, title: str, chunks: list[dict[str, Any]], criteria: list[str] | None = None
) -> dict[str, Any]:
    """The explain-back item every published skill needs: `assessment_requirements` list the
    'explanation' dimension, and without such an item the skill can never be mastered (found by
    the first live rehearsal, 2026-09-23). The rubric follows the skill's success criteria when
    the draft has them, otherwise three literal criteria keyed on the lecture's own vocabulary."""
    terms = salient_terms([str(c["text"]) for c in chunks])
    if criteria:
        rubric = rubric_from_criteria(criteria, terms)
    else:
        rubric = [
            {
                "criterion": f"Says what '{title}' is for — the problem it solves or the question it answers",
                "keywords": terms[:4],
            },
            {
                "criterion": "Explains how it works in the learner's own words, step by step",
                "keywords": terms[4:8] or terms,
            },
            {
                "criterion": "Gives one concrete example, value or step taken from the lecture",
                "keywords": terms,
            },
        ]
    return {
        "skill": slug,
        "kind": "explain_back",
        "item": {
            "prompt": f"Explain '{title}' in your own words, as the lecture teaches it: what it is "
            "for, how it works, and one concrete example or step.",
        },
        "rubric": rubric,
        "source_chunk_id": str(chunks[0]["id"]) if chunks else None,
        "auto": True,
    }


def propose_payload(mat: SectionMaterial, *, domain: str = "ai_ml") -> dict[str, Any]:
    """One skill per lecture, prerequisites in lecture order, a LearningObject whose goal restates
    the lecture, and cloze candidates cut from the source. Success criteria, examples and exercises
    are left empty on purpose: transcript openers are not worked examples and a template criterion
    would silence the validator's warning. Every field is meant to be edited; nothing here is a
    claim about the material's truth."""
    skills: list[dict[str, Any]] = []
    objects: list[dict[str, Any]] = []
    assessments: list[dict[str, Any]] = []
    prev_slug: str | None = None
    for lec, slug in zip(mat.lectures, lecture_slugs(mat), strict=False):
        title = str(lec["lecture"])
        chunks = lec["chunks"]
        where = f"{mat.course} › {mat.section}" if mat.section else mat.course
        n_docs = len(lec.get("documents") or [])
        docs_note = f", {n_docs} documents" if n_docs > 1 else ""
        skills.append(
            {
                "slug": slug,
                "title": title,
                "description": f"Lecture '{title}' in {where} ({len(chunks)} source passages{docs_note}).",
                "success_criteria": [],
                "assessment_requirements": {
                    "dimensions": ["recall", "explanation"],
                    "min_items": 1,
                },
                "example_applications": [],
                "prerequisites": [prev_slug] if prev_slug else [],
            }
        )
        objects.append(
            {
                "skill": slug,
                "concept": title,
                "goal": f"Understand and explain '{title}' as taught in {mat.course}.",
                "examples": [],
                "exercises": [],
                "success_criteria": [],
                "sources": [c["id"] for c in chunks[:MAX_SOURCES_PER_OBJECT]],
            }
        )
        for cz in _cloze_candidates(title, chunks):
            assessments.append({"skill": slug, **cz})
        assessments.append(explain_back_item(slug, title, chunks))
        prev_slug = slug
    return {
        "domain": domain,
        "course": mat.course,
        "section": mat.section,
        "skills": skills,
        "learning_objects": objects,
        "assessments": assessments,
    }


# ----------------------------------------------------------------------------- validation
def selection_summary(mat: SectionMaterial) -> dict[str, Any]:
    """What the draft is built on, stored *in the payload* (`payload["selection"]`) so it survives
    every re-validation, edit and publish — a validation pass only re-derives the notes from it."""
    drafted = mat.lectures[:MAX_SKILLS_PER_DRAFT]
    return {
        "built_on": [
            {**d, "lecture": str(lec["lecture"])}
            for lec in drafted
            for d in lec.get("documents")
            or [
                {
                    "document_id": lec["document_id"],
                    "title": lec["title"],
                    "passages": len(lec["chunks"]),
                }
            ]
        ],
        "beyond_cap": [
            {"document_id": d["document_id"], "title": d["title"], "lecture": str(lec["lecture"])}
            for lec in mat.lectures[MAX_SKILLS_PER_DRAFT:]
            for d in lec.get("documents")
            or [{"document_id": lec["document_id"], "title": lec["title"]}]
        ],
        "cited_passages": sum(min(len(lec["chunks"]), MAX_SOURCES_PER_OBJECT) for lec in drafted),
        "unique_passages": mat.unique_chunks,
        "left_out": [
            {k: d[k] for k in ("document_id", "title", "role", "reason", "decided_by")}
            for d in mat.left_out
        ],
    }


def no_primary_message(mat: SectionMaterial, course: str, section: str | None) -> str:
    n_sup = sum(1 for d in mat.left_out if d["role"] == "supplemental")
    n_exc = sum(1 for d in mat.left_out if d["role"] == "excluded")
    n_dup = sum(1 for d in mat.left_out if d["role"] == "primary")
    return (
        f"no primary material in section '{section or '(no section)'}': {n_sup} supplemental, "
        f"{n_exc} excluded, {n_dup} primary without unique passages. Open 'Sources of {course}' "
        "and set at least one document with passages to primary."
    )


def selection_problems(selection: dict[str, Any] | None) -> list[Problem]:
    """The visible notes derived from `payload["selection"]`, so a reviewer never has to guess
    whether a bundled notebook shaped the lessons. Empty for drafts without a selection (hand-made
    or from before this slice)."""
    if not isinstance(selection, dict) or "built_on" not in selection:
        return []
    built = _dicts(selection.get("built_on"))
    beyond = _dicts(selection.get("beyond_cap"))
    notes = [
        Problem(
            "info",
            "draft",
            f"built on {len(built)} of {len(built) + len(beyond)} primary document(s); "
            f"{selection.get('cited_passages', 0)} of {selection.get('unique_passages', 0)} "
            "unique passages cited",
        )
    ]
    if beyond:
        names = ", ".join(f"'{d.get('title')}'" for d in beyond[:5])
        more = f", … {len(beyond) - 5} more" if len(beyond) > 5 else ""
        notes.append(
            Problem(
                "warning",
                "draft",
                f"{len(beyond)} primary document(s) beyond the {MAX_SKILLS_PER_DRAFT}-skill cap "
                f"were not drafted: {names}{more} — split the section or set them to supplemental",
            )
        )
    for d in _dicts(selection.get("left_out")):
        why = str(d.get("reason") or "") or "your choice, no reason given"
        notes.append(
            Problem(
                "info",
                "draft",
                f"not used ({d.get('role')}, {d.get('decided_by')}): '{d.get('title')}' — {why}",
            )
        )
    return notes


def check_acyclic(nodes: set[str], edges: list[tuple[str, str]]) -> None:
    """Kahn over (prerequisite → skill) edges; raises ValueError on a cycle."""
    indeg = dict.fromkeys(nodes, 0)
    out: dict[str, list[str]] = {n: [] for n in nodes}
    for pre, post in edges:
        if pre not in indeg or post not in indeg:
            continue
        indeg[post] += 1
        out[pre].append(post)
    queue = [k for k, v in indeg.items() if v == 0]
    seen = 0
    while queue:
        cur = queue.pop()
        seen += 1
        for nxt in out[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if seen != len(nodes):
        stuck = sorted(k for k, v in indeg.items() if v > 0)[:5]
        raise ValueError("involving " + ", ".join(stuck))


def _dicts(items: Any) -> list[dict[str, Any]]:
    return [x for x in (items if isinstance(items, list) else []) if isinstance(x, dict)]


async def validate_payload(db: AsyncSession, payload: dict[str, Any]) -> list[Problem]:
    """Errors block publishing; warnings are shown. Checks: shape, slugs, prerequisites (draft or
    already published), cycles over the draft **plus the published graph**, learning objects and
    assessments per skill (no orphans), assessment shapes, source chunks that still exist, and the
    pedagogy gaps a deterministic draft leaves open (criteria, exercises, guessable cloze)."""
    problems: list[Problem] = []
    skills = _dicts(payload.get("skills"))
    if not skills:
        problems.append(Problem("error", "draft", "no skills"))
    slugs = [str(s.get("slug") or "") for s in skills]
    if len(set(slugs)) != len(slugs):
        problems.append(Problem("error", "draft", "duplicate skill slugs"))
    known = {x for x in slugs if x}
    published_slug_of: dict[str, str] = {
        str(i): str(sl) for i, sl in (await db.execute(select(SkillNode.id, SkillNode.slug))).all()
    }
    published_slugs = set(published_slug_of.values())
    for s in skills:
        slug = str(s.get("slug") or "")
        if not slug or not s.get("title"):
            problems.append(Problem("error", slug or "?", "slug and title are required"))
        pres = s.get("prerequisites")
        if not isinstance(pres, list):
            problems.append(Problem("error", slug, "prerequisites must be a list of slugs"))
            pres = []
        for pre in pres:
            if str(pre) not in known and str(pre) not in published_slugs:
                problems.append(Problem("error", slug, f"unknown prerequisite '{pre}'"))
        if not s.get("success_criteria"):
            problems.append(Problem("warning", slug, "no success criteria"))
    # cycles: draft edges ∪ every published prerequisite edge (publish only ever adds edges)
    edges: list[tuple[str, str]] = [
        (published_slug_of[str(a)], published_slug_of[str(b)])
        for a, b in (
            await db.execute(
                select(SkillEdge.from_skill_id, SkillEdge.to_skill_id).where(
                    SkillEdge.kind == "prerequisite"
                )
            )
        ).all()
        if str(a) in published_slug_of and str(b) in published_slug_of
    ]
    for s in skills:
        if s.get("slug") and isinstance(s.get("prerequisites"), list):
            edges.extend((str(pre), str(s["slug"])) for pre in s["prerequisites"])
    try:
        check_acyclic(known | published_slugs, edges)
    except ValueError as e:
        problems.append(Problem("error", "draft", f"prerequisite cycle: {e}"))
    objects: dict[str, dict[str, Any]] = {}
    for o in _dicts(payload.get("learning_objects")):
        sk = str(o.get("skill") or "")
        if sk not in known:
            problems.append(Problem("error", "draft", f"learning object for unknown skill '{sk}'"))
        objects[sk] = o
    assessments = _dicts(payload.get("assessments"))
    by_skill: dict[str, int] = {}
    for a in assessments:
        sk = str(a.get("skill") or "")
        if sk not in known:
            problems.append(Problem("error", "draft", f"assessment for unknown skill '{sk}'"))
        by_skill[sk] = by_skill.get(sk, 0) + 1
        kind = a.get("kind")
        raw_item = a.get("item")
        item: dict[str, Any] = raw_item if isinstance(raw_item, dict) else {}
        if kind == "cloze" and not (item.get("text") and item.get("answers")):
            problems.append(Problem("error", sk, "cloze needs text and answers"))
        if kind == "mcq" and not (
            item.get("question") and item.get("options") and "answer" in item
        ):
            problems.append(Problem("error", sk, "mcq needs question, options, answer"))
        if kind == "explain_back" and not (item.get("prompt") and a.get("rubric")):
            problems.append(Problem("error", sk, "explain_back needs prompt and rubric"))
        if kind not in ("mcq", "cloze", "explain_back"):
            problems.append(Problem("error", sk, f"unsupported assessment kind {kind!r}"))
        if a.get("guessable"):
            problems.append(
                Problem(
                    "warning",
                    sk,
                    "cloze blanks a title word — guessable from the header; edit or replace it",
                )
            )
        if a.get("origin") == "model" and not a.get("source_chunk_id"):
            problems.append(
                Problem(
                    "warning",
                    sk,
                    "model-proposed item: no single passage linked — check it against the source",
                )
            )
    chunk_ids = {
        str(c) for o in objects.values() for c in (o.get("sources") or []) if isinstance(c, str)
    } | {str(a.get("source_chunk_id")) for a in assessments if a.get("source_chunk_id")}
    present: set[str] = set()
    if chunk_ids:
        present = {
            str(r)
            for r in (
                await db.execute(select(Chunk.id).where(Chunk.id.in_(list(chunk_ids))))
            ).scalars()
        }
    for s in skills:
        slug = str(s.get("slug") or "")
        obj = objects.get(slug)
        if obj is None:
            problems.append(Problem("error", slug, "no learning object"))
        else:
            if not obj.get("goal") or not obj.get("concept"):
                problems.append(Problem("error", slug, "learning object needs concept and goal"))
            missing = [c for c in (obj.get("sources") or []) if c not in present]
            if missing:
                problems.append(
                    Problem("error", slug, f"{len(missing)} source chunk(s) no longer exist")
                )
            if not obj.get("sources"):
                problems.append(Problem("warning", slug, "no source passages linked"))
            if not obj.get("exercises"):
                problems.append(
                    Problem(
                        "warning",
                        slug,
                        "no exercises: a new node needs a worked example, then a faded problem",
                    )
                )
        reqs = s.get("assessment_requirements")
        dims = (reqs.get("dimensions") if isinstance(reqs, dict) else None) or []
        if "explanation" in dims and not any(
            a.get("kind") == "explain_back" and str(a.get("skill")) == slug for a in assessments
        ):
            problems.append(
                Problem(
                    "warning",
                    slug,
                    "requirements list 'explanation' but there is no explain_back item",
                )
            )
        if by_skill.get(slug, 0) < 1:
            problems.append(Problem("error", slug, "at least one assessment is required"))
    return problems


def problems_json(problems: list[Problem]) -> list[dict[str, str]]:
    return [{"level": p.level, "where": p.where, "message": p.message} for p in problems]


# ----------------------------------------------------------------------------- drafts
async def create_draft(
    db: AsyncSession,
    learner_id: str,
    *,
    course: str,
    section: str | None,
    payload: dict[str, Any] | None = None,
    origin: str = "deterministic",
    model_call_id: str | None = None,
    notes: list[Problem] | None = None,
) -> CurriculumDraft:
    if payload is None:
        mat = await section_material(db, course, section)
        if not mat.lectures:
            raise ValueError(no_primary_message(mat, course, section))
        payload = propose_payload(mat)
        payload["selection"] = selection_summary(mat)
    selection_notes = selection_problems(payload.get("selection"))
    problems = list(notes or []) + selection_notes + await validate_payload(db, payload)
    draft = CurriculumDraft(
        learner_id=learner_id,
        course=course,
        section=section,
        title=f"{course}" + (f" › {section}" if section else ""),
        status="draft",
        origin=origin,
        payload_json=payload,
        validation_json=problems_json(problems),
        model_call_id=model_call_id,
    )
    db.add(draft)
    await db.commit()
    return draft


async def get_draft(db: AsyncSession, learner_id: str, draft_id: str) -> CurriculumDraft:
    d = await db.get(CurriculumDraft, draft_id)
    if d is None or d.learner_id != learner_id:
        raise KeyError("draft not found")
    return d


async def list_drafts(db: AsyncSession, learner_id: str) -> list[CurriculumDraft]:
    stmt = (
        select(CurriculumDraft)
        .where(CurriculumDraft.learner_id == learner_id)
        .order_by(CurriculumDraft.updated_at.desc())
    )
    return list((await db.execute(stmt)).scalars())


async def update_draft(
    db: AsyncSession, learner_id: str, draft_id: str, payload: dict[str, Any]
) -> CurriculumDraft:
    d = await get_draft(db, learner_id, draft_id)
    if d.status != "draft":
        raise ValueError(f"a {d.status} draft cannot be edited; create a new draft")
    d.payload_json = payload
    d.validation_json = problems_json(
        selection_problems(payload.get("selection")) + await validate_payload(db, payload)
    )
    d.version += 1
    await db.commit()
    return d


async def reject_draft(db: AsyncSession, learner_id: str, draft_id: str) -> CurriculumDraft:
    d = await get_draft(db, learner_id, draft_id)
    if d.status == "published":
        raise ValueError("a published draft cannot be rejected; publish a corrected draft instead")
    d.status = "rejected"
    await db.commit()
    return d


@dataclass
class PublishReport:
    skills: int = 0
    edges: int = 0
    learning_objects: int = 0
    assessments: int = 0
    new_object_versions: int = 0


async def publish_draft(db: AsyncSession, learner_id: str, draft_id: str) -> PublishReport:
    """Apply the payload: nodes upserted (course stamped), edges added, a **new** LearningObject
    version per skill (older versions stay — historical evidence keeps pointing at what was taught),
    assessments added when their content is new (existing rows untouched). Errors block."""
    d = await get_draft(db, learner_id, draft_id)
    if d.status == "published":
        raise ValueError("already published")
    payload = d.payload_json
    problems = selection_problems(payload.get("selection")) + await validate_payload(db, payload)
    errors = [p for p in problems if p.level == "error"]
    if errors:
        d.validation_json = problems_json(problems)
        await db.commit()
        raise ValueError(
            "draft has errors: " + "; ".join(f"{p.where}: {p.message}" for p in errors[:5])
        )
    report = PublishReport()
    domain = str(payload.get("domain") or "ai_ml")
    course = str(payload.get("course") or d.course)
    section = payload.get("section", d.section)
    # the skill's place in the course: section order (as `sections_of` lists them) × 1000 + the
    # lecture position in this draft — so the goal-narrowed next-skill pick follows the course
    # regardless of the order in which sections were published
    section_labels = [s["section"] for s in await sections_of(db, course)]
    section_index = section_labels.index(section) + 1 if section in section_labels else None
    ids: dict[str, str] = {}
    for position, s in enumerate(payload["skills"], start=1):
        node = (
            await db.execute(select(SkillNode).where(SkillNode.slug == s["slug"]))
        ).scalar_one_or_none()
        fields = dict(
            domain=domain,
            course=course,
            section=section,
            order_no=(section_index * 1000 + position) if section_index is not None else None,
            title=s["title"],
            description=s.get("description", ""),
            success_criteria_json=s.get("success_criteria", []),
            assessment_requirements_json=s.get("assessment_requirements", {}),
            example_applications_json=s.get("example_applications", []),
        )
        if node is None:
            node = SkillNode(slug=s["slug"], **fields)
            db.add(node)
            await db.flush()
        else:
            for k, v in fields.items():
                setattr(node, k, v)
        ids[s["slug"]] = node.id
        report.skills += 1
    for s in payload["skills"]:
        for pre in s.get("prerequisites", []):
            pre_id = ids.get(pre)
            if pre_id is None:
                row = (
                    await db.execute(select(SkillNode.id).where(SkillNode.slug == pre))
                ).scalar_one_or_none()
                pre_id = str(row) if row else None
            if pre_id is None:
                continue
            exists = (
                await db.execute(
                    select(SkillEdge).where(
                        SkillEdge.from_skill_id == pre_id,
                        SkillEdge.to_skill_id == ids[s["slug"]],
                        SkillEdge.kind == "prerequisite",
                    )
                )
            ).scalar_one_or_none()
            if exists is None:
                db.add(
                    SkillEdge(from_skill_id=pre_id, to_skill_id=ids[s["slug"]], kind="prerequisite")
                )
                report.edges += 1
    for lo in payload.get("learning_objects", []):
        skill_id = ids[lo["skill"]]
        latest = (
            await db.execute(
                select(LearningObject)
                .where(LearningObject.skill_id == skill_id)
                .order_by(LearningObject.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        fields = dict(
            concept=lo["concept"],
            goal=lo["goal"],
            examples_json=lo.get("examples", []),
            exercises_json=lo.get("exercises", []),
            sources_json=lo.get("sources", []),
            success_criteria_json=lo.get("success_criteria", []),
        )
        same = latest is not None and all(getattr(latest, k) == v for k, v in fields.items())
        if not same:
            db.add(
                LearningObject(
                    skill_id=skill_id, version=(latest.version + 1) if latest else 1, **fields
                )
            )
            report.new_object_versions += 1
        report.learning_objects += 1
    for a in payload.get("assessments", []):
        skill_id = ids[a["skill"]]
        item = {k: v for k, v in dict(a["item"]).items()}
        if a.get("source_chunk_id"):
            item["source_chunk_id"] = a["source_chunk_id"]
        item["draft_id"] = d.id
        dup = False
        for arow in (
            await db.execute(
                select(Assessment).where(
                    Assessment.skill_id == skill_id, Assessment.kind == a["kind"]
                )
            )
        ).scalars():
            core = {
                k: v
                for k, v in arow.item_json.items()
                if k not in ("seed_key", "draft_id", "source_chunk_id")
            }
            mine = {
                k: v
                for k, v in item.items()
                if k not in ("seed_key", "draft_id", "source_chunk_id")
            }
            if core == mine:
                dup = True
                break
        if dup:
            continue
        rubric_id = None
        if a.get("rubric"):
            rubric = AssessmentRubric(criteria_json=a["rubric"], version=1)
            db.add(rubric)
            await db.flush()
            rubric_id = rubric.id
        db.add(Assessment(skill_id=skill_id, kind=a["kind"], item_json=item, rubric_id=rubric_id))
        report.assessments += 1
    d.status = "published"
    d.published_at = utcnow_iso()
    d.validation_json = problems_json(problems)
    await db.commit()
    return report


# ----------------------------------------------------------------------------- source passages
@dataclass
class Passage:
    chunk_id: str
    text: str
    citation: str
    course: str | None
    section: str | None
    lecture: str | None
    source_type: str
    trust_tier: int
    document_title: str
    uri: str
    t_start: float | None
    t_end: float | None
    prev_text: str | None
    next_text: str | None


async def passage(db: AsyncSession, chunk_id: str) -> Passage | None:
    """The cited chunk with its provenance and neighbours (citation viewer); None when gone."""
    row = (
        await db.execute(
            select(Chunk, ChunkProvenance, DocumentVersion, Document)
            .join(ChunkProvenance, ChunkProvenance.chunk_id == Chunk.id)
            .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(Chunk.id == chunk_id)
        )
    ).first()
    if row is None:
        return None
    c, prov, ver, doc = row
    neighbours = {
        ch.ordinal: ch.text
        for ch in (
            await db.execute(
                select(Chunk).where(
                    Chunk.document_version_id == ver.id,
                    Chunk.ordinal.in_([c.ordinal - 1, c.ordinal + 1]),
                )
            )
        ).scalars()
    }
    time = (
        f" @{int(c.t_start // 60):02d}:{int(c.t_start % 60):02d}" if c.t_start is not None else ""
    )
    parts = [p for p in (prov.course, prov.section, prov.lecture) if p]
    return Passage(
        chunk_id=c.id,
        text=c.text,
        citation="[" + " › ".join(parts) + time + "]",
        course=prov.course,
        section=prov.section,
        lecture=prov.lecture,
        source_type=prov.source_type,
        trust_tier=prov.trust_tier,
        document_title=doc.title,
        uri=doc.uri,
        t_start=c.t_start,
        t_end=c.t_end,
        prev_text=neighbours.get(c.ordinal - 1),
        next_text=neighbours.get(c.ordinal + 1),
    )


def open_target(uri: str, roots: list[Path]) -> Path | None:
    """The local file behind a document URI, only when it is a plain file (no archive member, no
    URL, no empty path) that lies under one of the configured ingest roots. Anything else is not
    served: the path is shown to the learner instead."""
    if not uri or uri.startswith(("http://", "https://")) or "!/" in uri:
        return None
    try:
        p = Path(uri).expanduser().resolve()
    except (OSError, RuntimeError):
        return None
    if not p.is_file():
        return None
    if any(p == r or r in p.parents for r in roots):
        return p
    return None


def open_fragment(source_type: str, uri: str, t_start: float | None) -> str:
    """`#t=` for media (browsers seek), nothing else: PDF page numbers are not tracked."""
    if t_start is not None and (
        source_type in ("udemy_caption", "audio", "video", "transcript")
        or uri.lower().endswith((".mp4", ".mp3", ".m4a", ".webm", ".mov", ".wav"))
    ):
        return f"#t={int(t_start)}"
    return ""


# ----------------------------------------------------------------------------- content reports
async def file_report(
    db: AsyncSession,
    learner_id: str,
    *,
    kind: str,
    turn_id: str | None,
    chunk_id: str | None,
    skill_id: str | None,
    note: str,
    assessment_id: str | None = None,
) -> ContentReport:
    """A report is a row next to the evidence; it never rewrites a chunk, a turn or a grade."""
    r = ContentReport(
        learner_id=learner_id,
        kind=kind,
        turn_id=turn_id,
        chunk_id=chunk_id,
        skill_id=skill_id,
        assessment_id=assessment_id,
        note=note.strip(),
    )
    db.add(r)
    await db.commit()
    return r
