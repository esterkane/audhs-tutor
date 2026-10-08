"""Private source identities for correction review, never proof of semantic support."""

import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, ChunkProvenance, DocumentVersion


def references(item: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    direct = item.get("source_chunk_id")
    if isinstance(direct, str) and direct:
        refs.append(direct)
    listening = item.get("listening")
    if isinstance(listening, dict) and isinstance(listening.get("chunk_id"), str):
        refs.append(listening["chunk_id"])
    sources = item.get("sources", [])
    if isinstance(sources, list):
        for source in sources:
            ref = source.get("chunk_id") if isinstance(source, dict) else source
            if isinstance(ref, str) and ref:
                refs.append(ref)
    return sorted(set(refs))


async def capture(db: AsyncSession, item: dict[str, Any]) -> dict[str, Any]:
    refs = references(item)
    declared = item.get("sources", [])
    malformed = (
        not isinstance(declared, list)
        or any(
            not (isinstance(ref, str) and ref)
            and not (
                isinstance(ref, dict) and isinstance(ref.get("chunk_id"), str) and ref["chunk_id"]
            )
            for ref in declared
        )
        if isinstance(declared, list)
        else True
    )
    if "source_chunk_id" in item and item["source_chunk_id"] is not None:
        malformed |= not isinstance(item["source_chunk_id"], str) or not item["source_chunk_id"]
    if "listening" in item:
        clip = item["listening"]
        malformed |= (
            not isinstance(clip, dict)
            or not isinstance(clip.get("chunk_id"), str)
            or not clip.get("chunk_id")
        )
    if len(refs) > 64:
        return {"version": 1, "complete": False, "reason": "too_many_references", "items": []}
    entries: list[dict[str, Any]] = []
    for ref in refs:
        chunk = await db.get(Chunk, ref, populate_existing=True)
        if chunk is None:
            # Legacy challenges may have citation labels rather than IDs. Never guess.
            entries.append({"reference": ref, "status": "unresolved"})
            continue
        version = await db.get(DocumentVersion, chunk.document_version_id, populate_existing=True)
        provenance = await db.scalar(
            select(ChunkProvenance)
            .where(ChunkProvenance.chunk_id == chunk.id)
            .execution_options(populate_existing=True)
        )
        entries.append(
            {
                "reference": ref,
                "status": "available" if version and provenance else "incomplete",
                "document_version_id": chunk.document_version_id,
                "document_id": version.document_id if version else None,
                "document_hash": version.content_hash if version else None,
                "version": version.version if version else None,
                "text_hash": hashlib.sha256(chunk.text.encode()).hexdigest(),
                "t_start": chunk.t_start,
                "t_end": chunk.t_end,
                "provenance": {
                    field: getattr(provenance, field)
                    for field in (
                        "source_id",
                        "path",
                        "source_type",
                        "trust_tier",
                        "course",
                        "section",
                        "lecture",
                        "flags_json",
                    )
                }
                if provenance
                else None,
            }
        )
    return {
        "version": 1,
        "complete": not malformed
        and bool(entries)
        and all(entry["status"] == "available" for entry in entries),
        "items": entries,
    }
