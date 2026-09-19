"""Ingest a markdown source into SQLite (document / document_version / chunk / chunk_provenance).
Idempotent by content hash: an unchanged file is a no-op; a changed file gets a new version."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PROJECT_ROOT
from app.db.models import Chunk, ChunkProvenance, Document, DocumentVersion
from app.knowledge.ingest.markdown import approx_tokens, chunk_sections, parse_markdown


@dataclass
class IngestResult:
    document_id: str
    version_id: str
    version: int
    chunks: int
    changed: bool


async def ingest_markdown(
    db: AsyncSession,
    path: Path,
    *,
    skill_ids_by_slug: dict[str, str] | None = None,
    course: str | None = None,
    trust_tier: int | None = None,
) -> IngestResult:
    doc = parse_markdown(await asyncio.to_thread(path.read_text))
    meta = doc.meta
    try:
        default_uri = path.resolve().relative_to(PROJECT_ROOT).as_posix()  # noqa: ASYNC240
    except ValueError:
        default_uri = path.as_posix()
    uri = str(meta.get("uri") or default_uri)
    course = course or meta.get("course")
    # trust is decided by the caller (ingest policy), never by the document's own front matter
    trust = int(trust_tier if trust_tier is not None else 2)
    source_type = str(meta.get("source_type") or "doc")

    document = (await db.execute(select(Document).where(Document.uri == uri))).scalar_one_or_none()
    if document is None:
        document = Document(
            title=doc.title,
            source_type=source_type,
            uri=uri,
            course=course,
            section=meta.get("section"),
            lecture=meta.get("lecture"),
        )
        db.add(document)
        await db.flush()
    existing = (
        await db.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.content_hash == doc.content_hash,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        n = (
            await db.execute(select(func.count()).where(Chunk.document_version_id == existing.id))
        ).scalar_one()
        return IngestResult(document.id, existing.id, existing.version, int(n), changed=False)

    last = (
        await db.execute(
            select(func.max(DocumentVersion.version)).where(
                DocumentVersion.document_id == document.id
            )
        )
    ).scalar_one()
    version = DocumentVersion(
        document_id=document.id,
        content_hash=doc.content_hash,
        version=int(last or 0) + 1,
        publication_date=str(meta.get("publication_date"))
        if meta.get("publication_date")
        else None,
    )
    db.add(version)
    await db.flush()
    slug_map = skill_ids_by_slug or {}
    drafts = chunk_sections(doc)
    for d in drafts:
        chunk = Chunk(
            document_version_id=version.id,
            ordinal=d.ordinal,
            text=d.text,
            token_count=approx_tokens(d.text),
            skill_ids_json=[slug_map[s] for s in d.skill_slugs if s in slug_map],
        )
        db.add(chunk)
        await db.flush()
        db.add(
            ChunkProvenance(
                chunk_id=chunk.id,
                source_id=document.id,
                path=f"{uri}#{d.heading}",
                source_type=source_type,
                trust_tier=trust,
                course=course,
                section=meta.get("section"),
                lecture=d.heading,
            )
        )
    await db.commit()
    return IngestResult(document.id, version.id, version.version, len(drafts), changed=True)
