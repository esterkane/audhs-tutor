"""Read-only binding checks; callers must resolve owned records before calling.

This does not validate visual semantics, permissions, or an authored lifecycle.
It performs no persistence, model calls or competency updates.
The stored-record adapter reads the existing database only.
"""

import hashlib
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document, DocumentVersion, LearningObject
from app.schemas.visual_binding import VisualBinding


def validate_binding(
    binding: VisualBinding, obj: LearningObject, chunks: Mapping[str, Chunk]
) -> None:
    """Reject stale/misattributed references against server-resolved records.

    `chunks` must come from the repository, never a client-supplied snapshot.
    A source may be a subset of the object's sources, not an unrelated chunk.
    """
    if (binding.object_id, binding.object_version, binding.skill_id) != (
        obj.id,
        obj.version,
        obj.skill_id,
    ):
        raise ValueError("learning object identity/version mismatch")
    if binding.goal != obj.goal:
        raise ValueError("learning objective mismatch")
    for criterion in binding.criteria:
        if (
            criterion.index >= len(obj.success_criteria_json)
            or obj.success_criteria_json[criterion.index] != criterion.text
        ):
            raise ValueError("success criterion mismatch")
    for source in binding.sources:
        if source.chunk_id not in obj.sources_json:
            raise ValueError("source is not part of the learning object")
        chunk = chunks.get(source.chunk_id)
        if chunk is None or chunk.id != source.chunk_id:
            raise ValueError("source chunk unavailable")
        if chunk.document_version_id != source.document_version_id:
            raise ValueError("source version mismatch")
        if hashlib.sha256(chunk.text.encode("utf-8")).hexdigest() != source.text_sha256:
            raise ValueError("source text changed")


async def validate_stored_binding(db: AsyncSession, binding: VisualBinding) -> None:
    """Check persisted content without flushing/discarding caller changes.

    This is not an authorization check or an acceptance transaction. Callers must
    authorize access and revalidate within any later authored-version write.
    Exact historical versions are intentional; never substitute the latest one.
    """
    # Column projections bypass stale ORM identity-map objects and pending edits.
    with db.no_autoflush:
        row = (
            (
                await db.execute(
                    select(
                        LearningObject.id,
                        LearningObject.version,
                        LearningObject.skill_id,
                        LearningObject.goal,
                        LearningObject.success_criteria_json,
                        LearningObject.sources_json,
                    ).where(LearningObject.id == binding.object_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ValueError("learning object unavailable")
        source_rows = (
            (
                await db.execute(
                    select(Chunk.id, Chunk.document_version_id, Chunk.text)
                    .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
                    .join(Document, Document.id == DocumentVersion.document_id)
                    .where(Chunk.id.in_([source.chunk_id for source in binding.sources]))
                )
            )
            .mappings()
            .all()
        )
    obj = LearningObject(**row)
    chunks = {str(source["id"]): Chunk(**source) for source in source_rows}
    validate_binding(binding, obj, chunks)
