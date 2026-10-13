"""Bounded owner-scoped reads; raw source snapshots are never response payloads."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import AuthoredVisualDocument as Document
from app.db.models import AuthoredVisualReview as Review
from app.db.models import AuthoredVisualSourceSnapshot as Snapshot
from app.db.models import AuthoredVisualVersion as Version
from app.kernel.authored_visuals import digest, require_current_trust, resolve_target
from app.schemas.authored_visuals import SPEC, VisualOrigin
from app.schemas.visual_history import (
    VisualDocumentSummary,
    VisualReviewRecord,
    VisualVersionDetail,
    VisualVersionSummary,
)
from app.schemas.visual_relationship import MAX_RELATIONSHIP_BYTES


async def document(db: AsyncSession, owner: str, document_id: str) -> Document:
    row = await db.scalar(
        select(Document).where(Document.id == document_id, Document.learner_id == owner)
    )
    if row is None:
        raise AppError("not_found", "Visual unavailable.", 404)
    return row


async def documents(
    db: AsyncSession, owner: str, archived: bool, offset: int, limit: int
) -> list[VisualDocumentSummary]:
    rows = await db.scalars(
        select(Document)
        .where(Document.learner_id == owner, Document.archived == archived)
        .order_by(Document.updated_at.desc(), Document.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [VisualDocumentSummary.model_validate(row, from_attributes=True) for row in rows]


async def versions(
    db: AsyncSession, owner: str, document_id: str, offset: int, limit: int
) -> list[VisualVersionSummary]:
    await document(db, owner, document_id)
    rows = await db.scalars(
        select(Version)
        .where(Version.learner_id == owner, Version.document_id == document_id)
        .order_by(Version.version.desc())
        .offset(offset)
        .limit(limit)
    )
    return [VisualVersionSummary.model_validate(row, from_attributes=True) for row in rows]


async def version(db: AsyncSession, owner: str, document_id: str, version_id: str) -> Version:
    await document(db, owner, document_id)
    row = await db.scalar(
        select(Version).where(
            Version.learner_id == owner,
            Version.document_id == document_id,
            Version.id == version_id,
        )
    )
    if row is None:
        raise AppError("not_found", "Visual version unavailable.", 404)
    return row


async def reviews(
    db: AsyncSession, owner: str, document_id: str, version_id: str, offset: int, limit: int
) -> list[VisualReviewRecord]:
    await version(db, owner, document_id, version_id)
    rows = await db.scalars(
        select(Review)
        .where(Review.learner_id == owner, Review.version_id == version_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [VisualReviewRecord.model_validate(row, from_attributes=True) for row in rows]


async def detail(
    db: AsyncSession, owner: str, document_id: str, version_id: str, threshold: int
) -> VisualVersionDetail:
    row = await version(db, owner, document_id, version_id)
    result = VisualVersionDetail(
        **VisualVersionSummary.model_validate(row, from_attributes=True).model_dump(),
        spec=None,
        grounding_now="invalid_content",
    )
    if (
        len(row.spec_json.encode()) > MAX_RELATIONSHIP_BYTES
        or digest(row.spec_json) != row.content_sha256
    ):
        return result
    try:
        spec = SPEC.validate_json(row.spec_json)
    except ValueError:
        return result
    result.spec = spec
    try:
        result.origin = VisualOrigin.model_validate(
            {key: row.origin_json.get(key) for key in ("kind", "model", "prompt_version")}
        )
    except ValueError:
        # Missing restored provenance stays unknown, never learner-authored by default.
        result.origin = None
    snapshot = await db.scalar(
        select(Snapshot.snapshot_json).where(
            Snapshot.learner_id == owner, Snapshot.version_id == version_id
        )
    )
    if snapshot is None or digest(snapshot) != row.snapshot_sha256:
        result.grounding_now = "snapshot_unavailable"
        return result
    try:
        target = await resolve_target(db, owner, spec)
    except AppError:
        result.grounding_now = "unavailable_or_changed"
        return result
    if target.grounding == "unknown" or digest(target.snapshot) != row.snapshot_sha256:
        result.grounding_now = "unavailable_or_changed"
        return result
    try:
        await require_current_trust(db, target.source_ids, threshold)
    except AppError:
        result.grounding_now = "source_excluded"
        return result
    result.grounding_now = "sources_recorded" if target.source_ids else "ungrounded"
    return result
