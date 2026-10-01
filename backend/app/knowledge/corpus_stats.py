"""Read models over the corpus tables for the Corpus screen (thin routers, ADR-0007 layering)."""

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, ChunkProvenance, Document, DocumentVersion, IndexState
from app.knowledge.reindex import latest_version_ids
from app.schemas.corpus import CourseStats, DocumentOut, IndexStateOut

FLAGGED = case(
    (ChunkProvenance.flags_json != "[]", 1), else_=0
)  # sum(bool) collapses to 1 on SQLite
UNIQUE = Chunk.duplicate_of.is_(None)


async def course_stats(db: AsyncSession, versions: list[str]) -> list[CourseStats]:
    if not versions:
        return []
    stmt = (
        select(
            Document.course,
            func.count(func.distinct(Document.id)),
            func.count(Chunk.id),
            func.sum(FLAGGED),
            func.group_concat(func.distinct(ChunkProvenance.source_type)),
            func.group_concat(func.distinct(ChunkProvenance.trust_tier)),
        )
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .join(Chunk, Chunk.document_version_id == DocumentVersion.id)
        .join(ChunkProvenance, ChunkProvenance.chunk_id == Chunk.id)
        .where(DocumentVersion.id.in_(versions), UNIQUE)
        .group_by(Document.course)
        .order_by(Document.course)
    )
    out = []
    for course, docs, chunks, flagged, types, tiers in (await db.execute(stmt)).all():
        out.append(
            CourseStats(
                course=course or "(no course)",
                documents=int(docs),
                chunks=int(chunks),
                flagged=int(flagged or 0),
                source_types=sorted(str(types or "").split(",")),
                trust_tiers=sorted(int(t) for t in str(tiers or "").split(",") if t != ""),
            )
        )
    return out


async def totals(db: AsyncSession, versions: list[str]) -> tuple[int, int, int, int]:
    """documents, versions, unique chunks, flagged unique chunks."""
    n_docs = (await db.execute(select(func.count()).select_from(Document))).scalar_one()
    n_versions = (await db.execute(select(func.count()).select_from(DocumentVersion))).scalar_one()
    if not versions:
        return int(n_docs), int(n_versions), 0, 0
    n_chunks = (
        await db.execute(
            select(func.count()).where(Chunk.document_version_id.in_(versions), UNIQUE)
        )
    ).scalar_one()
    flagged = (
        await db.execute(
            select(func.count())
            .select_from(ChunkProvenance)
            .join(Chunk, Chunk.id == ChunkProvenance.chunk_id)
            .where(
                Chunk.document_version_id.in_(versions), UNIQUE, ChunkProvenance.flags_json != "[]"
            )
        )
    ).scalar_one()
    return int(n_docs), int(n_versions), int(n_chunks), int(flagged)


async def index_state(db: AsyncSession, collection: str) -> IndexStateOut | None:
    state = (
        await db.execute(select(IndexState).where(IndexState.collection == collection))
    ).scalar_one_or_none()
    if state is None:
        return None
    return IndexStateOut(
        collection=state.collection,
        embedding_registry_id=state.embedding_registry_id,
        embedding_version=state.embedding_version,
        dims=state.dims,
        chunk_count=state.chunk_count,
        last_reindex=state.last_reindex,
    )


async def list_documents(db: AsyncSession, course: str | None = None) -> list[DocumentOut]:
    versions = await latest_version_ids(db)
    if not versions:
        return []
    stmt = (
        select(
            Document,
            DocumentVersion,
            func.count(Chunk.id),
            func.sum(FLAGGED),
            func.max(ChunkProvenance.trust_tier),
        )
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .outerjoin(Chunk, (Chunk.document_version_id == DocumentVersion.id) & UNIQUE)
        .outerjoin(ChunkProvenance, ChunkProvenance.chunk_id == Chunk.id)
        .where(DocumentVersion.id.in_(versions))
        .group_by(Document.id, DocumentVersion.id)
        .order_by(Document.course, Document.section, Document.title)
    )
    if course:
        stmt = stmt.where(Document.course == course)
    return [
        DocumentOut(
            id=d.id,
            title=d.title,
            source_type=d.source_type,
            uri=d.uri,
            course=d.course,
            section=d.section,
            lecture=d.lecture,
            version=v.version,
            chunks=int(n),
            flagged=int(f or 0),
            trust_tier=int(t if t is not None else 2),
            ingested_at=v.ingested_at,
        )
        for d, v, n, f, t in (await db.execute(stmt)).all()
    ]
