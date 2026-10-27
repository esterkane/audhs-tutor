"""Owner-requested source retirement: remove reusable content, retain historical identities.

This module does not delete learner answers, attempts, events, sessions or private authored notes.
Excluded source tokens share the publication policy's digests; they are not learning subjects.
"""

import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import unquote

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Assessment,
    AssessmentRubric,
    Chunk,
    ChunkProvenance,
    CourseSource,
    CurriculumDraft,
    Document,
    DocumentVersion,
    LearningObject,
    Representation,
    ReviewItem,
    SkillNode,
)

EXCLUDED_PROVIDER_HASHES = frozenset(
    {
        "583e17796e6a79e518b3b699d5fac2e9b758fea3904fed4937af0753e2c26759",
        "016d473857f1029884ec80ede8ae486f33d2fdad9411d63cd2aab11097ee997c",
    }
)


def excluded(value: str, hashes: frozenset[str] = EXCLUDED_PROVIDER_HASHES) -> bool:
    decoded = unquote(unquote(value))
    return any(
        hashlib.sha256(token.lower().encode()).hexdigest() in hashes
        for token in re.findall(r"[A-Za-z]+", decoded)
    )


def batches(values: list[str], size: int = 400) -> Iterator[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


@dataclass(frozen=True)
class RetirementPlan:
    documents: list[str]
    chunks: list[str]
    courses: list[str]
    paths: list[str]
    skills: list[str]
    drafts: list[str]

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()

    def summary(self) -> dict[str, int | str]:
        return {
            "documents": len(self.documents),
            "chunks": len(self.chunks),
            "courses": len(self.courses),
            "source_paths": len(self.paths),
            "skills": len(self.skills),
            "drafts": len(self.drafts),
            "digest": self.digest(),
        }


async def plan(
    db: AsyncSession, hashes: frozenset[str] = EXCLUDED_PROVIDER_HASHES
) -> RetirementPlan:
    rows = list(
        await db.execute(select(Document.id, Document.uri, Document.course, Document.title))
    )
    courses = sorted(
        {
            row.course
            for row in rows
            if row.course and excluded(" ".join([row.uri, row.course, row.title]), hashes)
        }
    )
    chosen = [
        row
        for row in rows
        if row.course in courses
        or excluded(" ".join([row.uri, row.course or "", row.title]), hashes)
    ]
    docs = sorted(row.id for row in chosen)
    chunks: list[str] = []
    paths = {row.uri for row in chosen if row.uri}
    for ids in batches(docs):
        versions = select(DocumentVersion.id).where(DocumentVersion.document_id.in_(ids))
        for identity, path in await db.execute(
            select(Chunk.id, ChunkProvenance.path)
            .outerjoin(ChunkProvenance, ChunkProvenance.chunk_id == Chunk.id)
            .where(Chunk.document_version_id.in_(versions))
        ):
            chunks.append(identity)
            if path:
                paths.add(path)
    source_ids = set(chunks) | set(docs)

    def references(value: object) -> bool:
        if isinstance(value, str):
            return value in source_ids or excluded(value, hashes)
        if isinstance(value, list):
            return any(references(item) for item in value)
        if isinstance(value, dict):
            return any(references(item) for item in value.values())
        return False

    skills = set(
        await db.scalars(
            select(SkillNode.id).where(
                SkillNode.course.in_(courses), SkillNode.owner_learner_id.is_(None)
            )
        )
    )
    for identity, sources in await db.execute(
        select(LearningObject.skill_id, LearningObject.sources_json)
        .join(SkillNode, SkillNode.id == LearningObject.skill_id)
        .where(SkillNode.owner_learner_id.is_(None))
    ):
        if references(sources):
            skills.add(identity)
    drafts = [
        row.id
        for row in await db.scalars(
            select(CurriculumDraft).where(CurriculumDraft.origin != "knowledge_authored")
        )
        if row.course in courses or references(row.payload_json)
    ]
    return RetirementPlan(
        docs, sorted(chunks), courses, sorted(paths), sorted(skills), sorted(drafts)
    )


async def redact(db: AsyncSession, selected: RetirementPlan) -> dict[str, int | str]:
    """Called only after verified backup and index deletion. Caller commits the transaction."""
    for ids in batches(selected.chunks):
        await db.execute(
            update(Chunk)
            .where(Chunk.id.in_(ids))
            .values(
                text="", token_count=0, norm_hash=None, skill_ids_json=[], t_start=None, t_end=None
            )
        )
        await db.execute(
            update(ChunkProvenance)
            .where(ChunkProvenance.chunk_id.in_(ids))
            .values(
                path="",
                trust_tier=0,
                course=None,
                section=None,
                lecture=None,
                flags_json=["content_removed"],
            )
        )
    for ids in batches(selected.documents):
        await db.execute(
            update(Document)
            .where(Document.id.in_(ids))
            .values(
                title="Removed course source",
                uri="",
                course=None,
                section=None,
                lecture=None,
                source_type="removed",
            )
        )
        await db.execute(
            update(CourseSource)
            .where(CourseSource.document_id.in_(ids))
            .values(role="excluded", reason="Source content removed at the owner's request")
        )
    for ids in batches(selected.skills):
        objects = list(
            await db.scalars(select(LearningObject.id).where(LearningObject.skill_id.in_(ids)))
        )
        for object_ids in batches(objects):
            await db.execute(
                update(Representation)
                .where(Representation.object_id.in_(object_ids))
                .values(content="", provenance_json={"content_removed": True})
            )
            await db.execute(
                update(LearningObject)
                .where(LearningObject.id.in_(object_ids))
                .values(
                    concept="Removed course material",
                    goal="",
                    sources_json=[],
                    examples_json=[],
                    exercises_json=[],
                    success_criteria_json=[],
                )
            )
        rubric_ids = list(
            await db.scalars(
                select(Assessment.rubric_id).where(
                    Assessment.skill_id.in_(ids), Assessment.rubric_id.is_not(None)
                )
            )
        )
        await db.execute(
            update(Assessment)
            .where(Assessment.skill_id.in_(ids))
            .values(item_json={"content_removed": True})
        )
        for rid in rubric_ids:
            shared = await db.scalar(
                select(Assessment.id)
                .where(Assessment.rubric_id == rid, Assessment.skill_id.not_in(selected.skills))
                .limit(1)
            )
            if shared is None:
                await db.execute(
                    update(AssessmentRubric)
                    .where(AssessmentRubric.id == rid)
                    .values(criteria_json=[])
                )
        await db.execute(
            update(ReviewItem)
            .where(ReviewItem.skill_id.in_(ids))
            .values(active=False, prompt_json={"content_removed": True})
        )
        await db.execute(
            update(SkillNode)
            .where(SkillNode.id.in_(ids))
            .values(
                title="Retired historical skill",
                description="",
                course=None,
                section=None,
                success_criteria_json=[],
                assessment_requirements_json={},
                example_applications_json=[],
            )
        )
    for ids in batches(selected.drafts):
        await db.execute(
            update(CurriculumDraft)
            .where(CurriculumDraft.id.in_(ids))
            .values(
                title="Removed course draft",
                course=None,
                section=None,
                payload_json={"content_removed": True},
                validation_json=[],
            )
        )
    return selected.summary()


async def is_redacted(db: AsyncSession, selected: RetirementPlan) -> bool:
    for ids in batches(selected.documents):
        count = await db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.id.in_(ids), Document.source_type == "removed")
        )
        if count != len(ids):
            return False
    for ids in batches(selected.chunks):
        count = await db.scalar(
            select(func.count()).select_from(Chunk).where(Chunk.id.in_(ids), Chunk.text == "")
        )
        if count != len(ids):
            return False
    for ids in batches(selected.drafts):
        count = await db.scalar(
            select(func.count())
            .select_from(CurriculumDraft)
            .where(
                CurriculumDraft.id.in_(ids),
                CurriculumDraft.payload_json["content_removed"].as_boolean().is_(True),
            )
        )
        if count != len(ids):
            return False
    return True
