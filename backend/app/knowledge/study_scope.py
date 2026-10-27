"""Request-local retrieval gate: old corpus is not ordinary study evidence."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document
from app.kernel.learning_scope import reference_before
from app.knowledge.repository import ChunkRecord, RetrievalRepository, SearchFilters, SearchResult


class StudyRepository:
    def __init__(self, base: RetrievalRepository, db: AsyncSession, learner_id: str) -> None:
        self.base, self.db, self.learner_id = base, db, learner_id
        self.collection = base.collection

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)

    async def search(
        self, query: str, filters: SearchFilters | None = None, k: int = 8
    ) -> SearchResult:
        cutoff = await reference_before(self.db, self.learner_id)
        if cutoff is None:
            return await self.base.search(query, filters, k)
        allowed = set(
            await self.db.scalars(select(Document.id).where(Document.created_at > cutoff))
        )
        narrowed = (filters or SearchFilters()).model_copy(deep=True)
        if narrowed.document_ids is not None:
            allowed.intersection_update(narrowed.document_ids)
        narrowed.document_ids = sorted(allowed) or ["__no_active_learning_documents__"]
        return await self.base.search(query, narrowed, k)

    async def upsert(self, chunks: list[ChunkRecord]) -> int:
        return await self.base.upsert(chunks)

    async def existing_ids(self, ids: list[str]) -> set[str]:
        return await self.base.existing_ids(ids)

    async def delete(self, ids: list[str]) -> None:
        await self.base.delete(ids)

    async def count(self) -> int:
        return await self.base.count()

    async def reindex(self, chunks: list[ChunkRecord]) -> int:
        return await self.base.reindex(chunks)
