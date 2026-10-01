"""Rebuild Qdrant from SQLite (latest document version per document). SQLite is the system of record."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.base import utcnow_iso
from app.db.models import Chunk, ChunkProvenance, DocumentVersion, IndexState
from app.knowledge.provenance import Provenance
from app.knowledge.qdrant_hybrid import QdrantHybridRepository
from app.knowledge.repository import ChunkRecord
from app.knowledge.rerank import FastembedReranker
from app.models_ai import registry
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import EmbeddingProvider, ModelSpec, TaskClass
from app.models_ai.routing import NoModelReady, Router


async def latest_version_ids(db: AsyncSession) -> list[str]:
    sub = (
        select(DocumentVersion.document_id, func.max(DocumentVersion.version).label("v"))
        .group_by(DocumentVersion.document_id)
        .subquery()
    )
    stmt = select(DocumentVersion.id).join(
        sub,
        (sub.c.document_id == DocumentVersion.document_id) & (sub.c.v == DocumentVersion.version),
    )
    return list((await db.execute(stmt)).scalars().all())


async def load_chunks(db: AsyncSession) -> list[ChunkRecord]:
    return await records_for_versions(db, await latest_version_ids(db))


async def records_for_versions(db: AsyncSession, versions: list[str]) -> list[ChunkRecord]:
    """Unique (non-duplicate) chunks of the given versions, ready for the index."""
    if not versions:
        return []
    return await _records(db, Chunk.document_version_id.in_(versions))


async def records_for_chunk_ids(db: AsyncSession, chunk_ids: list[str]) -> list[ChunkRecord]:
    if not chunk_ids:
        return []
    return await _records(db, Chunk.id.in_(chunk_ids))


async def _records(db: AsyncSession, where: Any) -> list[ChunkRecord]:
    stmt = (
        select(Chunk, ChunkProvenance, DocumentVersion.document_id)
        .join(ChunkProvenance, ChunkProvenance.chunk_id == Chunk.id)
        .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
        .where(where, Chunk.duplicate_of.is_(None))
        .order_by(DocumentVersion.document_id, Chunk.ordinal)
    )
    out = []
    for chunk, prov, doc_id in (await db.execute(stmt)).all():
        out.append(
            ChunkRecord(
                id=chunk.id,
                text=chunk.text,
                document_id=doc_id,
                ordinal=chunk.ordinal,
                skill_ids=list(chunk.skill_ids_json or []),
                provenance=Provenance(
                    source_id=prov.source_id,
                    path=prov.path,
                    source_type=prov.source_type,
                    trust_tier=prov.trust_tier,
                    course=prov.course,
                    section=prov.section,
                    lecture=prov.lecture,
                    t_start=chunk.t_start,
                    t_end=chunk.t_end,
                ),
            )
        )
    return out


async def embed_spec(db: AsyncSession, settings: Settings) -> ModelSpec:
    route = await Router(settings.routing_profile).resolve(db, TaskClass.EMBED)
    return await registry.get_spec(db, route.registry_id)


async def reranker_for(db: AsyncSession, settings: Settings) -> FastembedReranker | None:
    """The reranker is optional: only a `ready` registry entry routed for TaskClass.RERANK is used."""
    try:
        route = await Router(settings.routing_profile).resolve(db, TaskClass.RERANK)
    except NoModelReady:
        return None
    spec = await registry.get_spec(db, route.registry_id)
    cache = settings.models_dir_resolved / "fastembed"
    if (
        not cache.exists()
    ):  # registry says ready but the artefact is gone: never download at search time
        return None
    return FastembedReranker(spec.model, cache_dir=cache, registry_id=spec.registry_id)


async def build_repo(
    db: AsyncSession,
    settings: Settings,
    *,
    embedding_version: int = 1,
    embedder: EmbeddingProvider | None = None,
) -> QdrantHybridRepository:
    from qdrant_client import AsyncQdrantClient

    spec = await embed_spec(db, settings)
    emb = embedder or OllamaProvider(settings.ollama_host)
    dims = len((await emb.embed(spec, ["probe"]))[0])
    return QdrantHybridRepository(
        AsyncQdrantClient(url=settings.qdrant_url),
        emb,
        spec,
        dims=dims,
        embedding_version=embedding_version,
        reranker=await reranker_for(db, settings),
        max_per_document=settings.retrieval_max_per_document,
    )


async def reindex_all(
    db: AsyncSession, settings: Settings, *, embedding_version: int = 1
) -> tuple[str, int]:
    repo = await build_repo(db, settings, embedding_version=embedding_version)
    try:
        chunks = await load_chunks(db)
        n = await repo.reindex(chunks)
        state = (
            await db.execute(select(IndexState).where(IndexState.collection == repo.collection))
        ).scalar_one_or_none()
        if state is None:
            state = IndexState(
                collection=repo.collection,
                embedding_registry_id=repo.embed_spec.registry_id,
                embedding_version=embedding_version,
                dims=repo.dims,
            )
            db.add(state)
        state.chunk_count = n
        state.last_reindex = utcnow_iso()
        state.embedding_registry_id = repo.embed_spec.registry_id
        await db.commit()
        return repo.collection, n
    finally:
        await repo.client.close()
