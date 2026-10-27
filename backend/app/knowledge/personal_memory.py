"""Version-bound personal writing retrieval; SQLite remains authoritative."""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import CurriculumDraft
from app.db.traces import write_retrieval_trace
from app.kernel.learning_scope import created_visible
from app.knowledge.provenance import Provenance
from app.knowledge.repository import ChunkRecord, RetrievalRepository, SearchFilters
from app.schemas.knowledge_authoring import PersonalMemory


async def excerpts(db: AsyncSession, learner_id: str, exclude: str) -> list[PersonalMemory]:
    rows = (
        await db.scalars(
            select(CurriculumDraft)
            .where(
                CurriculumDraft.learner_id == learner_id,
                created_visible(learner_id, CurriculumDraft.created_at),
                CurriculumDraft.id != exclude,
                CurriculumDraft.status.in_(["draft", "published"]),
                CurriculumDraft.origin == "knowledge_authored",
            )
            .order_by(CurriculumDraft.id)
            .execution_options(populate_existing=True)
        )
    ).all()
    result = []
    for row in rows:
        a = row.payload_json.get("authoring") or {}
        pieces = [("notes", a.get("notes", "")), ("explanation", a.get("explanation", ""))]
        for q in (a.get("research") or {}).get("questions", []):
            for key in ["findings", "evidence", "unresolved", "section"]:
                pieces.append((f"{q['id']}:{key}", q.get(key, "")))
        for kind, content in pieces:
            for offset in range(0, len(content), 1600):
                text = content[offset : offset + 1800]
                if not text.strip():
                    continue
                identity = json.dumps([learner_id, row.id, row.version, kind, offset, text])
                result.append(
                    PersonalMemory(
                        id=hashlib.sha256(identity.encode()).hexdigest(),
                        draft_id=row.id,
                        version=row.version,
                        title=row.title,
                        kind=kind,
                        text=text,
                    )
                )
    return result


async def selected(
    db: AsyncSession, learner_id: str, draft_id: str, ids: list[str]
) -> list[PersonalMemory]:
    if not ids:
        return []
    allowed = {m.id: m for m in await excerpts(db, learner_id, draft_id)}
    if any(i not in allowed for i in ids):
        raise AppError(
            "memory_changed",
            "An earlier note changed or is unavailable. Remove it and search again before asking the tutor.",
            409,
        )
    return [allowed[i] for i in dict.fromkeys(ids)]


def index_id(memory: PersonalMemory) -> str:
    # Vector identity depends on EXACT embedding input and document identity, not save version.
    # Returned/selected memory IDs still include the current version and are revalidated.
    value = ["personal-content-v1", memory.draft_id, memory.title, memory.kind, memory.text]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()


async def search(
    db: AsyncSession,
    repo: RetrievalRepository,
    learner_id: str,
    draft_id: str,
    query: str,
    indexed: set[str] | None = None,
) -> list[PersonalMemory]:
    items = await excerpts(db, learner_id, draft_id)
    if not items:
        return []
    by_id = {index_id(m): m for m in items}
    present = await repo.existing_ids(list(by_id))
    missing = [(cid, m) for cid, m in by_id.items() if cid not in present]
    records = [
        ChunkRecord(
            id=cid,
            text=m.title + "\n" + m.kind + "\n" + m.text,
            document_id=cid,
            provenance=Provenance(
                source_id=m.draft_id,
                path=f"/curriculum?draft={m.draft_id}",
                source_type="personal_note",
                trust_tier=0,
                course=learner_id,
            ),
        )
        for cid, m in missing
    ]
    if records:
        await repo.upsert(records)
        if indexed is not None:
            indexed.update(cid for cid, _ in missing)
    # Explicit allowlist excludes other learners, deleted/rejected and older revisions.
    result = await repo.search(
        query, SearchFilters(course=learner_id, document_ids=list(by_id)), k=6
    )
    result.trace.learner_id = learner_id
    await write_retrieval_trace(db, result.trace)
    return [by_id[h.chunk.id] for h in result.hits if h.chunk.id in by_id][:6]
