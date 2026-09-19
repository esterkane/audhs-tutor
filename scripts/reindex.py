#!/usr/bin/env python3
"""Rebuild the Qdrant collection from SQLite (chunks + provenance). SQLite is the system of record.
usage: reindex.py [--embedding-version N] [--batch 64]"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from qdrant_client import AsyncQdrantClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.base import utcnow_iso  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.models import (  # noqa: E402
    Chunk,
    ChunkProvenance,
    Document,
    DocumentVersion,
    IndexState,
)
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.knowledge.provenance import Provenance  # noqa: E402
from app.knowledge.qdrant_hybrid import QdrantHybridRepository  # noqa: E402
from app.knowledge.repository import ChunkRecord  # noqa: E402
from app.models_ai import registry  # noqa: E402
from app.models_ai.ollama import OllamaProvider  # noqa: E402
from app.models_ai.provider import TaskClass  # noqa: E402
from app.models_ai.routing import Router  # noqa: E402


async def load_chunks(db: AsyncSession) -> list[ChunkRecord]:
    stmt = (
        select(Chunk, ChunkProvenance, DocumentVersion.document_id)
        .join(ChunkProvenance, ChunkProvenance.chunk_id == Chunk.id)
        .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .order_by(Document.id, Chunk.ordinal)
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


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--embedding-version", type=int, default=1)
    ap.add_argument("--batch", type=int, default=64)
    args = ap.parse_args()
    s = get_settings()
    upgrade_to_head(s.sync_database_url)
    engine = make_engine(s.database_url_resolved)
    try:
        async with make_session_factory(engine)() as db:
            route = await Router(s.routing_profile).resolve(db, TaskClass.EMBED)
            spec = await registry.get_spec(db, route.registry_id)
            embedder = OllamaProvider(s.ollama_host)
            dims = len((await embedder.embed(spec, ["probe"]))[0])
            repo = QdrantHybridRepository(
                AsyncQdrantClient(url=s.qdrant_url),
                embedder,
                spec,
                dims=dims,
                embedding_version=args.embedding_version,
                batch_size=args.batch,
            )
            chunks = await load_chunks(db)
            print(
                f"reindexing {len(chunks)} chunks into {repo.collection} with {spec.registry_id} ({dims}d)"
            )
            n = await repo.reindex(chunks)
            state = (
                await db.execute(select(IndexState).where(IndexState.collection == repo.collection))
            ).scalar_one_or_none()
            if state is None:
                state = IndexState(
                    collection=repo.collection,
                    embedding_registry_id=spec.registry_id,
                    embedding_version=args.embedding_version,
                    dims=dims,
                )
                db.add(state)
            state.chunk_count = n
            state.last_reindex = utcnow_iso()
            state.embedding_registry_id = spec.registry_id
            await db.commit()
            print(f"done: {n} points; index_state updated")
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
