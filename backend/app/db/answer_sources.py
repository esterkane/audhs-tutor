"""Read-only comparison of saved retrieval text hashes with current local corpus records."""

import hashlib
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, DocumentVersion, TutorAnswer
from app.schemas.answers import SavedSourceCheck, SavedSourceStatus


async def check(db: AsyncSession, learner_id: str, answer_id: str) -> SavedSourceCheck:
    answer = await db.scalar(
        select(TutorAnswer).where(TutorAnswer.id == answer_id, TutorAnswer.learner_id == learner_id)
    )
    if answer is None:
        raise KeyError("saved answer not found")
    raw_hashes = answer.metadata_json.get("source_text_hashes")
    hashes = raw_hashes if isinstance(raw_hashes, dict) else {}
    raw_sources = answer.metadata_json.get("sources")
    sources = raw_sources if isinstance(raw_sources, list) else []
    ids = list(
        dict.fromkeys(
            [
                s["chunk_id"]
                for s in sources
                if isinstance(s, dict) and isinstance(s.get("chunk_id"), str)
            ]
            + [key for key in hashes if isinstance(key, str)]
        )
    )
    # At most three reads regardless of citation count; no per-source round trips.
    newest_versions = (
        select(DocumentVersion.document_id, func.max(DocumentVersion.version).label("newest"))
        .group_by(DocumentVersion.document_id)
        .subquery()
    )
    rows = await db.execute(
        select(Chunk.id, Chunk.text, DocumentVersion.version, newest_versions.c.newest)
        .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
        .join(newest_versions, newest_versions.c.document_id == DocumentVersion.document_id)
        .where(Chunk.id.in_(ids[:100]))
    )
    current = {row.id: row for row in rows}
    result: list[SavedSourceStatus] = []
    for id_ in ids[:100]:
        chunk = current.get(id_)
        if chunk is None:
            result.append(SavedSourceStatus(chunk_id=id_, status="missing"))
            continue
        expected = hashes.get(id_)
        status: Literal["unchanged", "changed", "missing", "unverifiable"] = "unverifiable"
        if (
            isinstance(expected, str)
            and len(expected) == 64
            and all(c in "0123456789abcdef" for c in expected)
        ):
            status = (
                "unchanged"
                if hashlib.sha256(chunk.text.encode()).hexdigest() == expected
                else "changed"
            )
        result.append(
            SavedSourceStatus(
                chunk_id=id_,
                status=status,
                newer_version=chunk.newest > chunk.version,
            )
        )
    return SavedSourceCheck(sources=result, omitted=max(0, len(ids) - 100))
