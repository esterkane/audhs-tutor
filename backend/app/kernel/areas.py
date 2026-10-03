"""Deterministic cross-course source organization; metadata matches are proposals, not truth."""

import asyncio
import re
from collections import defaultdict
from collections.abc import Iterator
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Chunk,
    ChunkProvenance,
    CurriculumDraft,
    Document,
    DocumentVersion,
    KnowledgeArea,
)
from app.kernel import curriculum
from app.kernel.assessment_quality import course_metadata, orientation_title

DEFAULTS = [
    (
        "python",
        "Python and programming",
        ["python", "funktionen", "kontrollstrukturen", "objektorientierung"],
    ),
    (
        "data",
        "Data analysis and databases",
        [
            "pandas",
            "numpy",
            "sql",
            "database",
            "datenbank",
            "data analysis",
            "data science",
            "statisti",
        ],
    ),
    (
        "ml",
        "Machine learning foundations",
        ["machine learning", "regression", "classification", "optimization", "gradient"],
    ),
    (
        "deep-learning",
        "Deep learning and transformers",
        ["deep learning", "neural", "neuronal", "pytorch", "tensor", "transformer", "attention"],
    ),
    ("rag", "Retrieval and RAG", ["rag", "retrieval", "embedding", "vector", "question answering"]),
    ("langchain", "LangChain and LangGraph", ["langchain", "langgraph", "lcel", "langmem"]),
    ("agents", "Agents and tool use", ["agent", "openclaw", "function calling", "tool use"]),
    ("mcp", "Model Context Protocol", ["mcp", "model context protocol", "model context protokoll"]),
    ("n8n", "n8n and workflow automation", ["n8n", "automation", "automatisierung", "workflow"]),
    (
        "local-ai",
        "Local models and inference",
        ["local ai", "local llm", "lokale", "ollama", "inference", "quantization", "quantisierung"],
    ),
    (
        "evaluation",
        "Evaluation, safety and observability",
        [
            "evaluation",
            "evaluat",
            "guardrail",
            "security",
            "sicherheit",
            "observability",
            "monitoring",
            "judging",
            "red team",
        ],
    ),
    (
        "finetuning",
        "Training and fine-tuning",
        ["fine-tun", "finetun", "lora", "training", "trainieren"],
    ),
    ("containers", "Docker and containers", ["docker", "container"]),
    (
        "deployment",
        "Deployment, cloud and DevOps",
        ["kubernetes", "devops", "deploy", "terraform", "aws", "azure", "gitops", "linux", "ci/cd"],
    ),
    (
        "multimodal",
        "Images, speech and multimodal AI",
        [
            "diffusion",
            "comfyui",
            "speech",
            "voice",
            "whisper",
            "audio",
            "bildgenerierung",
            "computer vision",
        ],
    ),
    (
        "prompts",
        "Prompts and context design",
        ["prompt", "context management", "kontextmanagement"],
    ),
]


async def seed(db: AsyncSession) -> None:
    existing = set((await db.execute(select(KnowledgeArea.slug))).scalars())
    for slug, title, terms in DEFAULTS:
        if slug not in existing:
            db.add(
                KnowledgeArea(
                    slug=slug,
                    title=title,
                    terms_json=terms,
                    description="Suggested from source titles and sections; edit the matching terms to refine it.",
                )
            )
    await db.commit()


async def get(db: AsyncSession, area_id: str) -> KnowledgeArea:
    area = await db.get(KnowledgeArea, area_id)
    if area is None:
        raise KeyError("area not found")
    return area


# Retain the explicitly stemmed terms shipped in the original catalog. Other terms
# match tokens (including ordinary English plurals), not arbitrary identifier prefixes.
_LEGACY_STEMS = {"statisti", "evaluat", "fine-tun", "finetun", "deploy"}


def _term_expressions(terms: list[Any] | tuple[str, ...]) -> Iterator[str]:
    for term in terms:
        value = str(term).strip().casefold()
        if not value:
            continue
        tail = "" if value in _LEGACY_STEMS else r"(?!\w)"
        if value in {
            "database",
            "tensor",
            "gradient",
            "regression",
            "classification",
            "optimization",
            "character",
            "prompt",
            "agent",
            "transformer",
            "container",
            "embedding",
            "vector",
            "guardrail",
            "workflow",
            "keyframe",
            "prototype",
        }:
            tail = r"s?(?!\w)"
        yield r"(?<!\w)" + re.escape(value) + tail


def _has_term(text: str, terms: list[Any]) -> bool:
    low = text.casefold()
    return any(re.search(expression, low) for expression in _term_expressions(terms))


def teachable_passage(text: str, terms: list[Any]) -> bool:
    """Bounded evidence filter, not a semantic quality guarantee."""
    body = curriculum._body(text)
    low = body.casefold()
    if (
        sum(
            marker in low
            for marker in (
                "report created:",
                "source files collected",
                "collected comps:",
                "rendering plug-ins:",
            )
        )
        >= 2
    ):
        return False
    opening = re.sub(r"^#+[^\n]*\n", "", body).strip()
    if course_metadata(body) or orientation_title(opening[:250]):
        return False
    if not passage_matches(text, terms):
        return False
    # Code is evidence only when a programming-language term itself is requested.
    # Do not admit RAG sample data just because it sits in a RAG lesson folder.
    languages = {
        "css": {"css"},
        "javascript": {"javascript", "js"},
        "python": {"python", "py"},
        "sql": {"sql"},
    }
    for term in terms:
        for language in languages.get(str(term).strip().casefold(), set()):
            code = re.search(r"```" + language + r"\s*\n(.*?)```", body, re.S | re.I)
            if code and len(re.findall(r"[A-Za-z_]\w*", code[1])) >= 8:
                return True
    prose = re.sub(r"```.*?```", " ", body, flags=re.S)
    return len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", prose)) >= 25


def match(doc: Document, terms: list[Any]) -> str | None:
    # A course-wide fallback is explicit; its chapters are not all assumed to teach the topic.
    for level, text in [
        ("title/section", " ".join([doc.title, doc.section or "", doc.lecture or ""])),
        ("course context", doc.course or ""),
    ]:
        if _has_term(text, terms):
            return level
    return None


def passage_matches(text: str, terms: list[Any]) -> bool:
    # Exclude the ingestion title/header: bundled example data may live in a topic folder
    # without teaching that topic (e.g. billing FAQs in a RAG exercise).
    body = text.split("\n", 1)[1] if "\n" in text else text
    return _has_term(body, terms)


async def source_rows(db: AsyncSession, area: KnowledgeArea) -> list[dict[str, Any]]:
    docs = list(
        (
            await db.execute(
                select(Document).order_by(Document.course, Document.title, Document.id)
            )
        ).scalars()
    )
    roles: dict[str, dict[str, Any]] = {}
    for course in {d.course for d in docs if d.course}:
        roles.update(await curriculum.source_roles(db, str(course)))
    out = []
    for d in docs:
        reason = match(d, area.terms_json)
        if reason:
            role = roles.get(
                d.id, {"role": "primary", "reason": "no course role", "decided_by": "suggested"}
            )
            out.append(
                {
                    "document_id": d.id,
                    "title": d.title,
                    "course": d.course,
                    "section": d.section,
                    "match": reason,
                    **role,
                }
            )
    return out


def _catalogue_counts(
    area_terms: tuple[tuple[str, tuple[str, ...]], ...],
    documents: tuple[tuple[str, str | None, str | None, str | None], ...],
) -> tuple[dict[str, int], dict[str, list[str]], dict[str, set[str]], int]:
    """Worker-only aggregation over immutable metadata; never receives ORM/session objects."""
    patterns = {
        identifier: (
            tuple(str(term).strip().casefold() for term in terms if str(term).strip()),
            re.compile("|".join(expressions)) if expressions else None,
        )
        for identifier, terms in area_terms
        for expressions in [list(_term_expressions(terms))]
    }
    counts = dict.fromkeys(patterns, 0)
    courses: dict[str, set[str]] = {identifier: set() for identifier in patterns}
    related: dict[str, set[str]] = {identifier: set() for identifier in patterns}
    grouped: dict[tuple[str, str | None], int] = defaultdict(int)
    for title, section, lecture, course in documents:
        grouped[(" ".join([title, section or "", lecture or ""]).casefold(), course)] += 1
    course_matches: dict[str | None, set[str]] = {}
    assigned = 0
    for (text, course), multiplicity in grouped.items():
        if course not in course_matches:
            low = (course or "").casefold()
            course_matches[course] = {
                identifier
                for identifier, (values, pattern) in patterns.items()
                if pattern is not None
                and any(value in low for value in values)
                and pattern.search(low)
            }
        members = course_matches[course] | {
            identifier
            for identifier, (values, pattern) in patterns.items()
            if identifier not in course_matches[course]
            and pattern is not None
            and any(value in text for value in values)
            and pattern.search(text)
        }
        if members:
            assigned += multiplicity
        for identifier in members:
            counts[identifier] += multiplicity
            if course:
                courses[identifier].add(course)
            related[identifier].update(members - {identifier})
    return (
        counts,
        {identifier: sorted(values) for identifier, values in courses.items()},
        related,
        assigned,
    )


async def catalogue(db: AsyncSession, learner_id: str) -> dict[str, Any]:
    areas = list((await db.execute(select(KnowledgeArea).order_by(KnowledgeArea.title))).scalars())
    document_rows = (
        await db.execute(
            select(Document.title, Document.section, Document.lecture, Document.course)
        )
    ).all()
    documents = tuple((row.title, row.section, row.lecture, row.course) for row in document_rows)
    area_terms = tuple((area.id, tuple(str(term) for term in area.terms_json)) for area in areas)
    counts, courses, related, assigned = await asyncio.to_thread(
        _catalogue_counts, area_terms, documents
    )
    drafts: dict[str, list[str]] = defaultdict(list)
    for d in (
        await db.execute(
            select(CurriculumDraft).where(
                CurriculumDraft.learner_id == learner_id,
                CurriculumDraft.area_id.is_not(None),
                CurriculumDraft.status != "rejected",
            )
        )
    ).scalars():
        drafts[str(d.area_id)].append(d.id)
    out = []
    for a in areas:
        out.append(
            {
                "id": a.id,
                "slug": a.slug,
                "title": a.title,
                "terms": a.terms_json,
                "description": a.description,
                "documents": counts[a.id],
                "courses": courses[a.id],
                "draft_ids": drafts[a.id],
                "related": [b.title for b in areas if b.id in related[a.id]],
            }
        )
    return {
        "areas": out,
        "unassigned_documents": len(documents) - assigned,
        "total_documents": len(documents),
    }


async def excerpts(
    db: AsyncSession, area: KnowledgeArea
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sources = await source_rows(db, area)
    # Primary and supplemental can provide evidence; excluded never does. Only direct title/section
    # matches drive new area drafts, avoiding course-title topic leakage.
    eligible = [s for s in sources if s["role"] != "excluded" and s["match"] == "title/section"]
    ids = [s["document_id"] for s in eligible]
    latest = (
        select(DocumentVersion.document_id, func.max(DocumentVersion.version).label("v"))
        .group_by(DocumentVersion.document_id)
        .subquery()
    )
    stmt = (
        select(Chunk, Document)
        .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .join(
            latest, (latest.c.document_id == Document.id) & (latest.c.v == DocumentVersion.version)
        )
        .where(Document.id.in_(ids), Chunk.duplicate_of.is_(None))
        .where(
            Chunk.id.in_(select(ChunkProvenance.chunk_id).where(ChunkProvenance.trust_tier >= 2))
        )
        .order_by(Document.course, Document.id, Chunk.ordinal)
    )

    # Round-robin across courses and documents, after bounded evidence filtering.
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_docs: set[str] = set()
    total = 0
    for chunk, doc in (await db.execute(stmt)).all():
        total += 1
        if doc.id in seen_docs or not teachable_passage(chunk.text[:1200], area.terms_json):
            continue
        seen_docs.add(doc.id)
        pools[doc.course or "Unlabelled source"].append(
            {
                "id": chunk.id,
                "text": chunk.text[:1200],
                "document_id": doc.id,
                "course": doc.course,
                "title": doc.title,
            }
        )
    chosen: list[dict[str, Any]] = []
    while pools and len(chosen) < 12:
        for course in list(pools):
            chosen.append(pools[course].pop(0))
            if not pools[course]:
                del pools[course]
            if len(chosen) == 12:
                break
    coverage = {
        "matched_documents": len(sources),
        "eligible_documents": len(ids),
        "eligible_passages": total,
        "selected_passages": len(chosen),
        "selected_courses": sorted({str(c["course"]) for c in chosen}),
        "basis": (
            "Direct metadata matches; trusted, latest, nonduplicate passages. "
            "Up to 12 documents, balanced across courses; first substantive topic-matching prose "
            "or requested-language code passage per document. "
            "Not exhaustive coverage."
        ),
    }
    return chosen, coverage
