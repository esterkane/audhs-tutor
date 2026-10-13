"""Atomic private authoring commands; never a learning assessment or export grant."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.base import new_id, utcnow_iso
from app.db.models import (
    AuthoredVisualDocument as Document,
)
from app.db.models import (
    AuthoredVisualOperation as Operation,
)
from app.db.models import (
    AuthoredVisualReview as Review,
)
from app.db.models import (
    AuthoredVisualSourceSnapshot as Snapshot,
)
from app.db.models import (
    AuthoredVisualVersion as Version,
)
from app.db.models import (
    Chunk,
    ChunkProvenance,
    LearnerProfile,
)
from app.kernel.answer_visual_binding import validate_answer_binding
from app.kernel.visual_binding import validate_stored_binding
from app.knowledge.provenance import QUARANTINE_FLAGS
from app.schemas.authored_visuals import (
    SPEC,
    AnswerRelationshipVisual,
    ArchiveVisual,
    ReviewVisual,
    SaveVisual,
    VisualOrigin,
    VisualReceipt,
    parse_command,
)
from app.schemas.visual_relationship import RelationshipVisual


def canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def conflict(message: str) -> AppError:
    return AppError("visual_conflict", message, 409)


@dataclass(frozen=True)
class Target:
    kind: str
    id: str
    snapshot: str
    source_ids: frozenset[str]
    grounding: str


async def resolve_target(
    db: AsyncSession, learner_id: str, spec: RelationshipVisual | AnswerRelationshipVisual
) -> Target:
    try:
        if isinstance(spec, AnswerRelationshipVisual):
            result = await validate_answer_binding(db, learner_id, spec.binding)
            ids = frozenset(
                s.chunk_id for check in result.source_checks.values() for s in check.sources
            )
            if not set(spec.source_chunk_ids) <= ids:
                raise ValueError("visual source is absent from answer history")
            return Target(
                "answer", spec.binding.answer_id, result.snapshot_json, ids, result.grounding
            )
        await validate_stored_binding(db, spec.binding)
        rows = (
            (
                await db.execute(
                    select(Chunk.id, Chunk.document_version_id, Chunk.text).where(
                        Chunk.id.in_([s.chunk_id for s in spec.binding.sources])
                    )
                )
            )
            .mappings()
            .all()
        )
        return Target(
            "lesson",
            spec.binding.object_id,
            canonical(
                {
                    "binding": spec.binding.model_dump(mode="json"),
                    "sources": sorted([dict(row) for row in rows], key=lambda row: row["id"]),
                }
            ),
            frozenset(s.chunk_id for s in spec.binding.sources),
            "sources_recorded",
        )
    except (KeyError, ValueError) as exc:
        raise conflict(
            "The target or source history changed or is unavailable. Refresh the draft."
        ) from exc


async def require_current_trust(db: AsyncSession, ids: frozenset[str], threshold: int) -> None:
    rows = (
        await db.execute(
            select(
                ChunkProvenance.chunk_id, ChunkProvenance.trust_tier, ChunkProvenance.flags_json
            ).where(ChunkProvenance.chunk_id.in_(ids))
        )
    ).all()
    if {row.chunk_id for row in rows} != ids or any(
        row.trust_tier < 1
        or (row.trust_tier < threshold and QUARANTINE_FLAGS.intersection(row.flags_json))
        for row in rows
    ):
        raise conflict("A source is unavailable or excluded by current trust settings.")


class VisualRepository:
    """Each command owns a fresh session. No caller drafts are committed/discarded.

    Return values are historical operation receipts, not a promise of current state
    on a later retry. API/UI adapters must refetch before presenting current status.
    """

    def __init__(
        self, factory: async_sessionmaker[AsyncSession], *, quarantine_below_trust: int = 2
    ):
        self.factory = factory
        self.threshold = quarantine_below_trust

    async def execute(
        self, learner_id: str, request_id: str, raw: bytes, *, origin: VisualOrigin | None = None
    ) -> VisualReceipt:
        if not request_id.strip() or len(request_id) > 128:
            raise ValueError("Provide a request identity of at most 128 characters")
        command = parse_command(raw)
        origin = origin or VisualOrigin()
        if not isinstance(command, SaveVisual) and origin != VisualOrigin():
            raise ValueError("Only saves carry generation origin")
        fingerprint = digest(
            canonical(
                {
                    "command": command.model_dump(mode="json"),
                    "origin": origin.model_dump(mode="json"),
                }
            )
        )
        async with self.factory() as db:
            try:
                await db.execute(text("BEGIN IMMEDIATE"))
                if await db.get(LearnerProfile, learner_id) is None:
                    raise AppError("not_found", "Learner unavailable.", 404)
                prior = await db.scalar(
                    select(Operation).where(
                        Operation.learner_id == learner_id, Operation.request_id == request_id
                    )
                )
                if prior is not None:
                    if prior.fingerprint != fingerprint:
                        raise conflict(
                            "This request identity was already used for a different action."
                        )
                    result = VisualReceipt.model_validate(prior.response_json)
                    await db.commit()
                    return result
                document = None
                if command.document_id:
                    document = await db.scalar(
                        select(Document).where(
                            Document.id == command.document_id, Document.learner_id == learner_id
                        )
                    )
                    if document is None:
                        raise AppError("not_found", "Visual unavailable.", 404)
                    if document.revision != command.expected_revision:
                        raise conflict("The document changed. Refresh before editing or reviewing.")
                if isinstance(command, SaveVisual):
                    result = await self._save(db, learner_id, document, command, origin)
                else:
                    assert document is not None
                    if isinstance(command, ArchiveVisual):
                        document.archived = command.archived
                        document.updated_at = utcnow_iso()
                        document.revision += 1
                        result = VisualReceipt(
                            action="archive",
                            document_id=document.id,
                            revision=document.revision,
                            archived=document.archived,
                        )
                    else:
                        result = await self._review(db, learner_id, document, command)
                db.add(
                    Operation(
                        learner_id=learner_id,
                        document_id=result.document_id,
                        request_id=request_id,
                        fingerprint=fingerprint,
                        response_json=result.model_dump(mode="json"),
                    )
                )
                await db.commit()
                return result
            except BaseException:
                await db.rollback()
                raise

    async def _save(
        self,
        db: AsyncSession,
        learner_id: str,
        document: Document | None,
        command: SaveVisual,
        origin: VisualOrigin,
    ) -> VisualReceipt:
        if document is not None and document.archived:
            raise conflict("Restore this document before editing it.")
        target = await resolve_target(db, learner_id, command.spec)
        if document is None:
            document = Document(id=new_id(), learner_id=learner_id, title=command.spec.title)
            db.add(document)
            await db.flush()
            number = 1
        else:
            previous = await db.scalar(
                select(Version)
                .where(
                    Version.document_id == document.id,
                    Version.learner_id == learner_id,
                )
                .order_by(Version.version.desc())
                .limit(1)
            )
            if previous is None or (previous.target_kind, previous.target_id) != (
                target.kind,
                target.id,
            ):
                raise conflict(
                    "An edit must explain the same target. Save a separate document instead."
                )
            number = (
                int(
                    (
                        await db.scalar(
                            select(func.max(Version.version)).where(
                                Version.document_id == document.id, Version.learner_id == learner_id
                            )
                        )
                    )
                    or 0
                )
                + 1
            )
            document.revision += 1
            document.title = command.spec.title
        document.updated_at = utcnow_iso()
        content = canonical(command.spec.model_dump(mode="json"))
        version = Version(
            id=new_id(),
            learner_id=learner_id,
            document_id=document.id,
            version=number,
            spec_json=content,
            content_sha256=digest(content),
            binding_json=canonical(command.spec.binding.model_dump(mode="json")),
            snapshot_sha256=digest(target.snapshot),
            target_kind=target.kind,
            target_id=target.id,
            origin_json={**origin.model_dump(mode="json"), "grounding_at_save": target.grounding},
        )
        db.add(version)
        await db.flush()
        db.add(
            Snapshot(learner_id=learner_id, version_id=version.id, snapshot_json=target.snapshot)
        )
        return VisualReceipt(
            action="save",
            document_id=document.id,
            revision=document.revision,
            version_id=version.id,
            content_sha256=version.content_sha256,
            snapshot_sha256=version.snapshot_sha256,
        )

    async def _review(
        self, db: AsyncSession, learner_id: str, document: Document, command: ReviewVisual
    ) -> VisualReceipt:
        if document.archived:
            raise conflict("Restore this document before reviewing it.")
        version = await db.scalar(
            select(Version).where(
                Version.id == command.version_id,
                Version.document_id == document.id,
                Version.learner_id == learner_id,
            )
        )
        if version is None:
            raise AppError("not_found", "Visual version unavailable.", 404)
        latest = await db.scalar(
            select(func.max(Version.version)).where(
                Version.document_id == document.id, Version.learner_id == learner_id
            )
        )
        if version.version != latest:
            raise conflict("A newer version exists. Review the latest version explicitly.")
        if (
            command.content_sha256 != version.content_sha256
            or command.snapshot_sha256 != version.snapshot_sha256
            or digest(version.spec_json) != version.content_sha256
        ):
            raise conflict("The reviewed version does not match the displayed content.")
        if command.decision == "accept":
            snapshot = await db.scalar(
                select(Snapshot.snapshot_json).where(
                    Snapshot.version_id == version.id, Snapshot.learner_id == learner_id
                )
            )
            if snapshot is None or digest(snapshot) != version.snapshot_sha256:
                raise conflict("Original grounding snapshot is unavailable. Keep this as a draft.")
            spec = SPEC.validate_json(version.spec_json)
            target = await resolve_target(db, learner_id, spec)
            if digest(target.snapshot) != version.snapshot_sha256 or target.grounding == "unknown":
                raise conflict("Target or grounding changed. Create and review a new draft.")
            await require_current_trust(db, target.source_ids, self.threshold)
        review = Review(
            id=new_id(),
            learner_id=learner_id,
            version_id=version.id,
            content_sha256=version.content_sha256,
            snapshot_sha256=version.snapshot_sha256,
            decision=command.decision,
            note=command.note,
        )
        db.add(review)
        document.revision += 1
        document.updated_at = utcnow_iso()
        return VisualReceipt(
            action="review",
            document_id=document.id,
            revision=document.revision,
            version_id=version.id,
            content_sha256=version.content_sha256,
            snapshot_sha256=version.snapshot_sha256,
            review_id=review.id,
        )
