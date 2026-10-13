"""Bounded owner-scoped reads; raw source snapshots are never response payloads."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.errors import AppError
from app.db.models import AuthoredVisualDocument as Document
from app.db.models import AuthoredVisualReview as Review
from app.db.models import AuthoredVisualSourceSnapshot as Snapshot
from app.db.models import AuthoredVisualVersion as Version
from app.db.models import TutorAnswer
from app.kernel.answer_visual_binding import resolve_answer_binding
from app.kernel.authored_visuals import digest, require_current_trust, resolve_target
from app.schemas.authored_visuals import SPEC, VisualOrigin
from app.schemas.visual_history import (
    AnswerVisualTarget,
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
    db: AsyncSession,
    owner: str,
    archived: bool,
    offset: int,
    limit: int,
    answer_id: str | None = None,
) -> list[VisualDocumentSummary]:
    query = select(Document).where(Document.learner_id == owner, Document.archived == archived)
    if answer_id is not None:
        answer = await db.scalar(
            select(TutorAnswer.id).where(
                TutorAnswer.id == answer_id,
                TutorAnswer.learner_id == owner,
                TutorAnswer.surface == "ask",
            )
        )
        if answer is None:
            raise AppError("not_found", "Ask answer unavailable.", 404)
        latest = aliased(Version)
        latest_id = (
            select(latest.id)
            .where(
                latest.document_id == Document.id,
                latest.learner_id == owner,
            )
            .order_by(latest.version.desc())
            .limit(1)
            .correlate(Document)
            .scalar_subquery()
        )
        # Current target only: restored history may contain older retargeted versions.
        query = query.where(
            select(Version.id)
            .where(
                Version.id == latest_id,
                Version.learner_id == owner,
                Version.target_kind == "answer",
                Version.target_id == answer_id,
            )
            .correlate(Document)
            .exists()
        )
    rows = await db.scalars(
        query.order_by(Document.updated_at.desc(), Document.id.desc()).offset(offset).limit(limit)
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


async def answer_target(db: AsyncSession, owner: str, answer_id: str) -> AnswerVisualTarget:
    try:
        resolved = await resolve_answer_binding(db, owner, answer_id)
    except KeyError:
        raise AppError("not_found", "Ask answer unavailable.", 404) from None
    source_ids = sorted(
        {source.chunk_id for check in resolved.source_checks.values() for source in check.sources}
    )
    grounding = resolved.grounding
    return AnswerVisualTarget(
        binding=resolved.binding,
        grounding="unknown"
        if grounding == "unknown"
        else ("sources_recorded" if grounding == "sources_recorded" else "ungrounded"),
        source_chunk_ids=source_ids[:64],
        sources_omitted=max(0, len(source_ids) - 64),
        issues=list(resolved.issues),
    )
