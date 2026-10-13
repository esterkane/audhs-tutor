"""Resolve explicit local evidence once, retaining exact source snapshots for saved replies."""

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import Chunk, ChunkProvenance, Document, DocumentVersion
from app.orchestrator.answer_check_binding import text_hash
from app.orchestrator.context import QUARANTINE_FLAGS, RetrievedChunk, data_block, escape_data
from app.orchestrator.tools import TUTOR_MIN_TRUST
from app.schemas.ask import AskSources


async def resolve(
    db: AsyncSession, selection: AskSources | None, quarantine_below_trust: int
) -> list[dict[str, Any]]:
    if selection is None:
        return []
    rows = await db.execute(
        select(Chunk, ChunkProvenance, DocumentVersion, Document)
        .join(ChunkProvenance, ChunkProvenance.chunk_id == Chunk.id)
        .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(Chunk.id.in_(selection.passage_ids))
        .execution_options(populate_existing=True)
    )
    by_id = {
        chunk.id: (chunk, provenance, version, document)
        for chunk, provenance, version, document in rows
    }
    if set(by_id) != set(selection.passage_ids):
        raise AppError(
            "source_unavailable",
            "A selected passage or its provenance is unavailable. Search and select again.",
            409,
        )
    result: list[dict[str, Any]] = []
    for index, identity in enumerate(selection.passage_ids, 1):
        chunk, provenance, version, document = by_id[identity]
        if provenance.trust_tier < TUTOR_MIN_TRUST or (
            provenance.trust_tier < quarantine_below_trust
            and QUARANTINE_FLAGS.intersection(provenance.flags_json)
        ):
            raise AppError(
                "source_excluded",
                "A selected passage is excluded by source trust settings. Remove it or search again.",
                422,
            )
        if text_hash(chunk.text) != selection.passage_hashes[identity]:
            raise AppError(
                "source_changed",
                "A selected passage changed. Search and select it again before asking.",
                409,
            )
        result.append(
            {
                "chunk_id": identity,
                "citation": f"S{index}: {document.title} (local version {version.version})",
                "source_key": f"S{index}",
                "text": chunk.text,
                "text_hash": text_hash(chunk.text),
                "document_id": document.id,
                "document_version_id": version.id,
                "document_version": version.version,
                "source_id": provenance.source_id,
                "source_type": provenance.source_type,
                "path": provenance.path,
                "course": provenance.course,
                "section": provenance.section,
                "lecture": provenance.lecture,
                "t_start": chunk.t_start,
                "t_end": chunk.t_end,
                "trust_tier": provenance.trust_tier,
                "flags": list(provenance.flags_json),
                "ingested_at": version.ingested_at,
            }
        )
    if sum(len(s["text"]) + len(s["citation"]) for s in result) > 16000:
        raise AppError(
            "sources_too_large",
            "Choose fewer or shorter passages (maximum 16,000 source characters).",
            422,
        )
    return result


def prompt_block(sources: list[dict[str, Any]]) -> str:
    return data_block(
        [
            RetrievedChunk(
                chunk_id=s["chunk_id"],
                text=s["text"],
                citation=escape_data(s["citation"]),
                trust_tier=s["trust_tier"],
                score=1,
                flagged=[],
            )
            for s in sources
        ],
        citation_style="source",
        include_trust=False,
    )


def validate_citation_ids(text: str, sources: list[dict[str, Any]]) -> None:
    supplied = {s["source_key"] for s in sources}
    if any(key not in supplied for key in re.findall(r"\[source:([^\]\n]+)\]", text)):
        raise AppError(
            "invalid_source_reference",
            "The model referenced a passage that was not supplied. The preview is retained "
            "but no completed answer was saved. Start a new request to try again.",
            422,
        )
