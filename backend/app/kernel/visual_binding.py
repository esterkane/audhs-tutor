"""Read-only binding checks; callers must resolve owned records before calling.

This does not validate visual semantics, permissions, or an authored lifecycle.
It performs no persistence, retrieval, model calls or competency updates.
"""

import hashlib
from collections.abc import Mapping

from app.db.models import Chunk, LearningObject
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
