"""Explicit notes-to-draft preparation. No model calls or learning evidence writes."""

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document, DocumentVersion, KnowledgeArea
from app.kernel.learning_scope import reference_before, require_current_material
from app.schemas.knowledge_authoring import KnowledgeMaterialInput


async def source_ids(
    db: AsyncSession, learner_id: str, upload_id: str | None, selected_text: str = ""
) -> list[str]:
    if not upload_id:
        return []
    doc = await db.get(Document, upload_id)
    if doc is None or f"/knowledge-authoring/{learner_id}/" not in doc.uri:
        raise ValueError("Uploaded source is unavailable for this learner")
    await require_current_material(db, learner_id, doc.created_at)
    latest = await db.scalar(
        select(DocumentVersion.id)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version.desc())
        .limit(1)
    )
    chunks = list(
        (
            await db.scalars(
                select(Chunk)
                .where(Chunk.document_version_id == latest, Chunk.duplicate_of.is_(None))
                .order_by(Chunk.ordinal)
            )
        ).all()
    )
    # Prefer the chosen excerpt, including sections beyond the start of a long upload.
    terms = set(re.findall(r"\w{3,}", selected_text.casefold()))

    def relevance(chunk: Chunk) -> float:
        words = set(re.findall(r"\w{3,}", chunk.text.casefold()))
        return len(terms & words) / max(1, len(words))

    selected = sorted(chunks, key=relevance, reverse=True)[:6]
    return [c.id for c in sorted(selected, key=lambda c: c.ordinal)]


async def payload_for(
    db: AsyncSession,
    learner_id: str,
    command: KnowledgeMaterialInput,
    slug: str,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if command.research and command.research.passage not in command.notes:
        earlier = (previous or {}).get("research") or {}
        if earlier.get("passage") != command.research.passage:
            raise ValueError("Select an exact passage from your source notes")
    area_id = None
    if command.focus_topic:
        area_id = await db.scalar(
            select(KnowledgeArea.id).where(KnowledgeArea.slug == "focus-" + command.focus_topic)
        )
    elif await reference_before(db, learner_id):
        raise ValueError("Choose the technology for this new knowledge material")
    sources = await source_ids(db, learner_id, command.upload_id, command.notes)
    authoring = {**(previous or {}), **command.model_dump(mode="json")}
    complete = all(
        v.strip()
        for v in [command.objective, command.explanation, command.worked_example, command.question]
    ) and bool(command.criteria)
    payload: dict[str, Any] = {
        "domain": command.domain.value,
        "area_id": area_id,
        "area_title": command.title,
        "authoring": authoring,
        "skills": [],
        "learning_objects": [],
        "assessments": [],
    }
    if not complete:
        return payload
    criteria = [c.strip() for c in command.criteria]
    if any(not c or len(c) > 4000 for c in criteria) or len(
        set(c.casefold() for c in criteria)
    ) != len(criteria):
        raise ValueError("Use distinct, nonempty criteria of at most 4000 characters")
    payload["skills"] = [
        {
            "slug": slug,
            "title": command.title,
            "description": command.objective,
            "prerequisites": [],
            "success_criteria": criteria,
            "assessment_requirements": {"dimensions": ["explanation"], "min_items": 1},
        }
    ]
    payload["learning_objects"] = [
        {
            "skill": slug,
            "concept": command.title,
            "goal": command.objective,
            "examples": [command.explanation, command.worked_example],
            "exercises": [command.question],
            "success_criteria": criteria,
            "sources": sources,
        }
    ]
    payload["assessments"] = [
        {
            "skill": slug,
            "kind": "explain_back",
            "origin": "learner_authored",
            "auto": False,
            "guessable": False,
            "source_chunk_id": sources[0] if sources else None,
            "item": {"prompt": command.question},
            "rubric": [
                {
                    "criterion": c,
                    "description": c + ". Accept equivalent correct reasoning.",
                    "weight": 1 / len(criteria),
                    "required_terms": [],
                }
                for c in criteria
            ],
        }
    ]
    return payload
