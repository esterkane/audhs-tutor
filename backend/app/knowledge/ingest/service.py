"""Ingest sources into SQLite (document / document_version / chunk / chunk_provenance) and the
retrieval index. SQLite is the system of record; the index is derived.

Invariants (tests/test_ingest.py):
- Idempotent by content hash against the *latest* version: unchanged file → no-op; changed file →
  new version; reverted file → the matching older version becomes the latest again (re-numbered).
- Duplicate chunks (same normalised body inside the same course, or across course-less documents)
  are stored with `duplicate_of` set and never indexed; forgetting the surviving document promotes
  the duplicates so the text stays retrievable.
- The index is written *before* the SQLite commit: an index failure rolls the version back and is
  reported, so the two stores never diverge silently. New chunks are upserted before old ones are
  deleted, so a retry is safe.
- Trust is decided by the caller, never by the file (ADR-0008); instruction-like patterns are
  flagged at ingest time and stored on the provenance row."""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PROJECT_ROOT
from app.db.models import Chunk, ChunkProvenance, Document, DocumentVersion
from app.knowledge.ingest.chunker import chunk_doc
from app.knowledge.ingest.loaders import iter_source_files, load_file
from app.knowledge.ingest.normalize import approx_tokens, norm_hash
from app.knowledge.ingest.types import SourceDoc
from app.knowledge.provenance import Provenance, flag_instruction_patterns
from app.knowledge.repository import ChunkRecord, RetrievalRepository


@dataclass
class IngestResult:
    document_id: str
    version_id: str
    version: int
    chunks: int  # unique chunks (indexed)
    changed: bool
    title: str = ""
    uri: str = ""
    course: str | None = None
    source_type: str = ""
    deduped: int = 0  # stored as duplicates, not indexed
    flagged: int = 0
    indexed: int = 0
    trust_updated: bool = False
    reverted: bool = False


@dataclass
class SkippedFile:
    path: str
    reason: str


@dataclass
class IngestReport:
    results: list[IngestResult] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)

    @property
    def files(self) -> int:
        return len(self.results) + len(self.skipped)

    def summary(self) -> dict[str, Any]:
        new = [r for r in self.results if r.changed]
        return {
            "files": self.files,
            "documents": len(self.results),
            "new_versions": len(new),
            "unchanged": len(self.results) - len(new),
            "skipped": len(self.skipped),
            "chunks": sum(r.chunks for r in new),
            "deduped": sum(r.deduped for r in new),
            "flagged": sum(r.flagged for r in new),
            "indexed": sum(r.indexed for r in new),
            "courses": sorted({r.course for r in self.results if r.course}),
        }


# ----------------------------------------------------------------------------- helpers
def _latest_subquery() -> Any:
    return (
        select(DocumentVersion.document_id, func.max(DocumentVersion.version).label("v"))
        .group_by(DocumentVersion.document_id)
        .subquery()
    )


async def _existing_hashes(
    db: AsyncSession, course: str | None, document_id: str
) -> dict[str, str]:
    """norm_hash → chunk id for unique chunks in the latest version of every *other* document of
    the same course (course-less documents dedupe against each other)."""
    latest = _latest_subquery()
    stmt = (
        select(Chunk.norm_hash, Chunk.id)
        .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
        .join(
            latest,
            (latest.c.document_id == DocumentVersion.document_id)
            & (latest.c.v == DocumentVersion.version),
        )
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(
            Document.id != document_id,
            Chunk.norm_hash.is_not(None),
            Chunk.duplicate_of.is_(None),
        )
    )
    stmt = (
        stmt.where(Document.course == course)
        if course is not None
        else stmt.where(Document.course.is_(None))
    )
    return {h: cid for h, cid in (await db.execute(stmt)).all() if h}


async def records_for_versions(db: AsyncSession, versions: list[str]) -> list[ChunkRecord]:
    from app.knowledge.reindex import records_for_versions as _records

    return await _records(db, versions)


async def _chunk_ids(db: AsyncSession, version_id: str, *, unique_only: bool) -> list[str]:
    stmt = select(Chunk.id).where(Chunk.document_version_id == version_id)
    if unique_only:
        stmt = stmt.where(Chunk.duplicate_of.is_(None))
    return list((await db.execute(stmt)).scalars().all())


async def _update_trust(
    db: AsyncSession, version_id: str, trust: int, repo: RetrievalRepository | None
) -> bool:
    """Unchanged content, different trust decision: update provenance rows and index payloads."""
    rows = list(
        (
            await db.execute(
                select(ChunkProvenance)
                .join(Chunk, Chunk.id == ChunkProvenance.chunk_id)
                .where(Chunk.document_version_id == version_id, ChunkProvenance.trust_tier != trust)
            )
        ).scalars()
    )
    if not rows:
        return False
    for r in rows:
        r.trust_tier = trust
    await db.flush()
    if repo is not None:
        ids = await _chunk_ids(db, version_id, unique_only=True)
        update = getattr(repo, "update_payload", None)
        if update is not None:
            await update(ids, {"trust_tier": trust})
        else:  # adapter without payload updates: re-upsert
            await repo.upsert(await records_for_versions(db, [version_id]))
    return True


async def _swap_index(
    db: AsyncSession,
    repo: RetrievalRepository,
    *,
    new_version_id: str,
    old_version_id: str | None,
    records: list[ChunkRecord] | None = None,
) -> int:
    """Upsert the new version's unique chunks first, then remove the old version's — a failure in
    between leaves both in the index, which a retry repairs; never a hole."""
    recs = records if records is not None else await records_for_versions(db, [new_version_id])
    n = await repo.upsert(recs) if recs else 0
    if old_version_id is not None:
        old_ids = await _chunk_ids(db, old_version_id, unique_only=True)
        if old_ids:
            await repo.delete(old_ids)
    return n


# ----------------------------------------------------------------------------- ingest
async def ingest_source(
    db: AsyncSession,
    doc: SourceDoc,
    *,
    skill_ids_by_slug: dict[str, str] | None = None,
    trust_tier: int = 2,
    repo: RetrievalRepository | None = None,
    dedupe: bool = True,
) -> IngestResult:
    document = (
        await db.execute(select(Document).where(Document.uri == doc.uri))
    ).scalar_one_or_none()
    if document is None:
        document = Document(
            title=doc.title,
            source_type=doc.source_type,
            uri=doc.uri,
            course=doc.course,
            section=doc.section,
            lecture=doc.lecture,
        )
        db.add(document)
        await db.flush()
    else:
        document.title, document.course = doc.title, doc.course or document.course
        document.section, document.lecture = doc.section, doc.lecture

    def result(**kw: Any) -> IngestResult:
        return IngestResult(
            document_id=document.id,
            title=doc.title,
            uri=doc.uri,
            course=doc.course,
            source_type=doc.source_type,
            **kw,
        )

    prev = (
        await db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    # unchanged: same hash as the latest version
    if prev is not None and prev.content_hash == doc.content_hash:
        retrusted = await _update_trust(db, prev.id, int(trust_tier), repo)
        n = len(await _chunk_ids(db, prev.id, unique_only=True))
        await db.commit()
        return result(
            version_id=prev.id,
            version=prev.version,
            chunks=n,
            changed=False,
            trust_updated=retrusted,
        )

    # reverted: an older version has this hash → it becomes the latest again
    older = (
        await db.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.content_hash == doc.content_hash,
            )
        )
    ).scalar_one_or_none()
    if older is not None and prev is not None:
        older.version = prev.version + 1
        await db.flush()
        await _update_trust(db, older.id, int(trust_tier), None)
        try:
            indexed = (
                await _swap_index(db, repo, new_version_id=older.id, old_version_id=prev.id)
                if repo is not None
                else 0
            )
        except Exception:
            await db.rollback()
            raise
        await db.commit()
        n = len(await _chunk_ids(db, older.id, unique_only=True))
        return result(
            version_id=older.id,
            version=older.version,
            chunks=n,
            changed=True,
            indexed=indexed,
            reverted=True,
        )

    version = DocumentVersion(
        document_id=document.id,
        content_hash=doc.content_hash,
        version=(prev.version if prev else 0) + 1,
        publication_date=str(doc.meta["publication_date"])
        if doc.meta.get("publication_date")
        else None,
    )
    db.add(version)
    await db.flush()

    slug_map = skill_ids_by_slug or {}
    seen: dict[str, str] = await _existing_hashes(db, doc.course, document.id) if dedupe else {}
    records: list[ChunkRecord] = []
    deduped = flagged = 0
    for ordinal, d in enumerate(chunk_doc(doc)):
        h = norm_hash(d.body or d.text)
        duplicate_of = seen.get(h) if dedupe else None
        flags = flag_instruction_patterns(d.text)
        chunk = Chunk(
            document_version_id=version.id,
            ordinal=ordinal,
            text=d.text,
            token_count=approx_tokens(d.text),
            t_start=d.t_start,
            t_end=d.t_end,
            skill_ids_json=[slug_map[s] for s in d.skill_slugs if s in slug_map],
            norm_hash=h,
            duplicate_of=duplicate_of,
        )
        db.add(chunk)
        await db.flush()
        lecture = doc.lecture or d.heading
        path = doc.uri if d.heading == doc.title else f"{doc.uri}#{d.heading}"
        db.add(
            ChunkProvenance(
                chunk_id=chunk.id,
                source_id=document.id,
                path=path,
                source_type=doc.source_type,
                trust_tier=int(trust_tier),
                course=doc.course,
                section=doc.section,
                lecture=lecture,
                flags_json=flags,
            )
        )
        if duplicate_of is not None:
            deduped += 1
            continue
        seen[h] = chunk.id
        flagged += bool(flags)
        records.append(
            ChunkRecord(
                id=chunk.id,
                text=d.text,
                document_id=document.id,
                ordinal=ordinal,
                skill_ids=list(chunk.skill_ids_json),
                provenance=Provenance(
                    source_id=document.id,
                    path=path,
                    source_type=doc.source_type,
                    trust_tier=int(trust_tier),
                    course=doc.course,
                    section=doc.section,
                    lecture=lecture,
                    t_start=d.t_start,
                    t_end=d.t_end,
                ),
            )
        )
    indexed = 0
    if repo is not None:
        try:
            indexed = await _swap_index(
                db,
                repo,
                new_version_id=version.id,
                old_version_id=prev.id if prev else None,
                records=records,
            )
        except Exception:
            await db.rollback()  # no version without its index
            raise
    await db.commit()
    return result(
        version_id=version.id,
        version=version.version,
        chunks=len(records),
        changed=True,
        deduped=deduped,
        flagged=flagged,
        indexed=indexed,
    )


async def ingest_file(
    db: AsyncSession,
    path: Path,
    *,
    root: Path | None = None,
    course: str | None = None,
    source_type: str | None = None,
    trust_tier: int = 2,
    skill_ids_by_slug: dict[str, str] | None = None,
    repo: RetrievalRepository | None = None,
) -> IngestResult:
    doc = await asyncio.to_thread(
        load_file, path, root=root, course=course, source_type=source_type
    )
    return await ingest_source(
        db, doc, skill_ids_by_slug=skill_ids_by_slug, trust_tier=trust_tier, repo=repo
    )


async def ingest_path(
    db: AsyncSession,
    src: Path,
    *,
    course: str | None = None,
    source_type: str | None = None,
    trust_tier: int = 2,
    skill_ids_by_slug: dict[str, str] | None = None,
    repo: RetrievalRepository | None = None,
) -> IngestReport:
    """Ingest one file or a directory tree. `src` itself is the root: `<src>/<Course>/<Section>/…`
    unless `course` is given, in which case `src` is the course folder. A single file is treated as
    `<Course>/<Section>/<file>` (root two levels up). Every failure is reported, never raised."""
    report = IngestReport()
    files = await asyncio.to_thread(iter_source_files, src)
    is_dir = await asyncio.to_thread(src.is_dir)
    # a single lecture file sits at <root>/<Course>/<Section>/<file>: the root is three levels up
    root = src if is_dir else src.parents[min(2, len(src.parents) - 1)]
    for path in files:
        try:
            res = await ingest_file(
                db,
                path,
                root=root,
                course=course,
                source_type=source_type,
                trust_tier=trust_tier,
                skill_ids_by_slug=skill_ids_by_slug,
                repo=repo,
            )
        except Exception as e:
            await db.rollback()
            report.skipped.append(SkippedFile(path.as_posix(), f"{type(e).__name__}: {e}"))
            continue
        report.results.append(res)
    return report


async def ingest_markdown(
    db: AsyncSession,
    path: Path,
    *,
    skill_ids_by_slug: dict[str, str] | None = None,
    course: str | None = None,
    trust_tier: int | None = None,
    repo: RetrievalRepository | None = None,
) -> IngestResult:
    """Seed path (owner-authored notes): front-matter `uri`/`course`/`source_type` are honoured,
    and a project-relative uri is used when none is given."""
    doc = await asyncio.to_thread(
        load_file, path, course=course, source_type="markdown", trust_front_matter=True
    )
    if doc.meta.get("uri") is None:
        try:
            doc.uri = path.resolve().relative_to(PROJECT_ROOT).as_posix()  # noqa: ASYNC240
        except ValueError:
            pass
    return await ingest_source(
        db,
        doc,
        skill_ids_by_slug=skill_ids_by_slug,
        trust_tier=2 if trust_tier is None else trust_tier,
        repo=repo,
    )


# ----------------------------------------------------------------------------- owner actions
async def retier_document(
    db: AsyncSession, document_id: str, trust: int, *, repo: RetrievalRepository | None = None
) -> bool:
    """Owner re-decides the trust tier of a document (latest version) without re-ingesting."""
    latest = (
        await db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is None:
        raise KeyError(document_id)
    changed = await _update_trust(db, latest.id, int(trust), repo)
    await db.commit()
    return changed


async def forget_document(
    db: AsyncSession, document_id: str, *, repo: RetrievalRepository | None = None
) -> int:
    """Remove a document with all versions, chunks and provenance from SQLite and the index.
    Chunks elsewhere that were deduplicated against this document are promoted (indexed again).
    Returns the number of chunks removed. Raises KeyError for an unknown id."""
    document = (
        await db.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise KeyError(document_id)
    version_ids = list(
        (
            await db.execute(
                select(DocumentVersion.id).where(DocumentVersion.document_id == document_id)
            )
        ).scalars()
    )
    chunk_ids = (
        list(
            (await db.execute(select(Chunk.id).where(Chunk.document_version_id.in_(version_ids))))
            .scalars()
            .all()
        )
        if version_ids
        else []
    )
    promoted: list[str] = []
    if chunk_ids:
        dups = list(
            (await db.execute(select(Chunk).where(Chunk.duplicate_of.in_(chunk_ids)))).scalars()
        )
        by_hash: dict[str, Chunk] = {}
        for c in sorted(dups, key=lambda c: (c.document_version_id, c.ordinal)):
            leader = by_hash.get(c.norm_hash or "")
            if leader is None:
                c.duplicate_of = None
                by_hash[c.norm_hash or ""] = c
                promoted.append(c.id)
            else:
                c.duplicate_of = leader.id
        await db.flush()
        await db.execute(delete(ChunkProvenance).where(ChunkProvenance.chunk_id.in_(chunk_ids)))
        await db.execute(delete(Chunk).where(Chunk.id.in_(chunk_ids)))
    if version_ids:
        await db.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids)))
    await db.delete(document)
    await db.flush()
    if repo is not None:
        if promoted:
            from app.knowledge.reindex import records_for_chunk_ids

            await repo.upsert(await records_for_chunk_ids(db, promoted))
        if chunk_ids:
            await repo.delete(chunk_ids)
    await db.commit()
    return len(chunk_ids)


async def rescan_flags(db: AsyncSession) -> tuple[int, int]:
    """Recompute instruction-pattern flags on every stored chunk (after a pattern change).
    Returns (chunks scanned, chunks whose flags changed)."""
    rows = (
        await db.execute(
            select(Chunk.text, ChunkProvenance).join(
                ChunkProvenance, ChunkProvenance.chunk_id == Chunk.id
            )
        )
    ).all()
    changed = 0
    for text, prov in rows:
        flags = flag_instruction_patterns(text)
        if list(prov.flags_json or []) != flags:
            prov.flags_json = flags
            changed += 1
    await db.commit()
    return len(rows), changed
