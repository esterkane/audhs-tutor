"""Explicit notes-to-draft preparation. No model calls or learning evidence writes."""

import hashlib
import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document, DocumentVersion, KnowledgeArea
from app.kernel.learning_scope import reference_before, require_current_material
from app.schemas.knowledge_authoring import (
    AcceptedCaseComparison,
    CaseComparison,
    ConceptRelationship,
    KnowledgeMaterialInput,
    ReadingPrequestion,
)


async def source_ids(
    db: AsyncSession,
    learner_id: str,
    upload_id: str | None,
    selected_text: str = "",
    version_id: str | None = None,
) -> list[str]:
    if not upload_id:
        if version_id:
            raise ValueError("An upload version requires its source document.")
        return []
    doc = await db.get(Document, upload_id)
    if doc is None or f"/knowledge-authoring/{learner_id}/" not in doc.uri:
        raise ValueError("Uploaded source is unavailable for this learner")
    await require_current_material(db, learner_id, doc.created_at)
    query = (
        select(DocumentVersion.id)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version.desc())
        .limit(1)
    )
    if version_id:
        query = query.where(DocumentVersion.id == version_id)
    latest = await db.scalar(query)
    if version_id and latest is None:
        raise ValueError("This extraction version does not belong to the selected upload.")
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

    def relevance(chunk: Chunk) -> tuple[bool, float]:
        words = set(re.findall(r"\w{3,}", chunk.text.casefold()))
        body = chunk.text.partition("\n")[2]
        exact = bool(version_id and selected_text and selected_text in body)
        return exact, len(terms & words) / max(1, len(words))

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
    version = command.upload_version_id
    if version is None and previous and previous.get("upload_id") == command.upload_id:
        version = previous.get("upload_version_id")
    sources = await source_ids(
        db,
        learner_id,
        command.upload_id,
        command.research.passage if version and command.research else command.notes,
        version,
    )
    authoring = {**(previous or {}), **command.model_dump(mode="json")}
    if version:
        authoring["upload_version_id"] = version
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


def accepted_prequestions(
    authoring: dict[str, Any], explanation: str, worked_example: str
) -> list[ReadingPrequestion]:
    """Read the published draft snapshot only; never infer or generate a question."""
    result = []
    for target, passage in (("explanation", explanation), ("worked_example", worked_example)):
        question = authoring.get(f"{target}_prequestion", "")
        if (
            not isinstance(question, str)
            or not question.strip()
            or len(question) > 1000
            or not passage.strip()
            or authoring.get(target) != passage
        ):
            continue
        identity = json.dumps(
            [target, passage, question], ensure_ascii=False, separators=(",", ":")
        )
        result.append(
            ReadingPrequestion(
                target=target,
                question=question,
                question_id=hashlib.sha256(identity.encode()).hexdigest(),
                content_sha256=hashlib.sha256(passage.encode()).hexdigest(),
            )
        )
    return result


def accepted_relationship(value: Any) -> ConceptRelationship | None:
    try:
        relationship = ConceptRelationship.model_validate(value)
    except ValueError:
        return None
    if not all(
        part.strip() for part in (relationship.source, relationship.link, relationship.target)
    ):
        return None
    if relationship.source.strip().casefold() == relationship.target.strip().casefold():
        return None
    return relationship


def accepted_case_comparison(value: Any) -> AcceptedCaseComparison | None:
    """Validate structure only. The learner authors and accepts the rationale."""
    if not isinstance(value, dict):
        return None
    try:
        pair = CaseComparison.model_validate(value)
    except ValueError:
        return None
    if (
        not pair.case_a.strip()
        or not pair.case_b.strip()
        or not pair.rationale.strip()
        or pair.failing_case is None
        or pair.case_a.strip() == pair.case_b.strip()
    ):
        return None
    parts = [pair.case_a, pair.case_b, pair.failing_case, pair.rationale]
    if pair.comparison_focus:
        parts.append(pair.comparison_focus)
    identity = json.dumps(
        parts,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return AcceptedCaseComparison(
        **pair.model_dump(), comparison_id=hashlib.sha256(identity.encode()).hexdigest()
    )
