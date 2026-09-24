"""Deterministic cross-course source organization; metadata matches are proposals, not truth."""

import re
from collections import defaultdict
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


def match(doc: Document, terms: list[Any]) -> str | None:
    # A course-wide fallback is explicit; its chapters are not all assumed to teach the topic.
    for level, text in [
        ("title/section", " ".join([doc.title, doc.section or "", doc.lecture or ""])),
        ("course context", doc.course or ""),
    ]:
        low = text.casefold()
        for term in terms:
            value = str(term).strip().casefold()
            if value and re.search(r"(?<!\w)" + re.escape(value), low):
                return level
    return None


def passage_matches(text: str, terms: list[Any]) -> bool:
    # Exclude the ingestion title/header: bundled example data may live in a topic folder
    # without teaching that topic (e.g. billing FAQs in a RAG exercise).
    body = text.split("\n", 1)[1] if "\n" in text else text
    return any(
        re.search(r"(?<!\w)" + re.escape(str(term).strip().casefold()), body.casefold())
        for term in terms
        if str(term).strip()
    )


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


async def catalogue(db: AsyncSession, learner_id: str) -> dict[str, Any]:
    areas = list((await db.execute(select(KnowledgeArea).order_by(KnowledgeArea.title))).scalars())
    docs = list((await db.execute(select(Document))).scalars())
    memberships = {a.id: {d.id for d in docs if match(d, a.terms_json)} for a in areas}
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
        members = memberships[a.id]
        out.append(
            {
                "id": a.id,
                "slug": a.slug,
                "title": a.title,
                "terms": a.terms_json,
                "description": a.description,
                "documents": len(members),
                "courses": sorted({str(d.course) for d in docs if d.id in members and d.course}),
                "draft_ids": drafts[a.id],
                "related": [b.title for b in areas if b.id != a.id and memberships[b.id] & members],
            }
        )
    assigned = set().union(*memberships.values()) if memberships else set()
    return {
        "areas": out,
        "unassigned_documents": len(docs) - len(assigned),
        "total_documents": len(docs),
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

    # Round-robin across courses and documents. Keep substantive prose rather than setup code.
    def prose_words(text: str) -> int:
        body = re.sub(r"```.*?```", " ", curriculum._body(text), flags=re.S)
        return len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", body))

    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_docs: set[str] = set()
    total = 0
    for chunk, doc in (await db.execute(stmt)).all():
        total += 1
        if (
            doc.id in seen_docs
            or prose_words(chunk.text) < 25
            or not passage_matches(chunk.text[:1200], area.terms_json)
        ):
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
            "Up to 12 documents, balanced across courses; first topic-matching prose passage per document. "
            "Not exhaustive coverage."
        ),
    }
    return chosen, coverage
