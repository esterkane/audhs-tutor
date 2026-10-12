"""Session-independent durable claims; no automatic takeover of uncertain work."""

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import new_id
from app.db.models import AskRequest
from app.db.workspace_requests import request_fingerprint


async def replay(
    db: AsyncSession, learner_id: str, key: str, payload: dict[str, Any]
) -> tuple[str, dict[str, Any]] | None:
    existing = await db.scalar(
        select(AskRequest).where(
            AskRequest.learner_id == learner_id,
            AskRequest.request_key == key,
        )
    )
    if existing is None:
        return None
    if existing.fingerprint != request_fingerprint(payload):
        raise AppError(
            "request_conflict", "This request identity belongs to a different question.", 409
        )
    if existing.response_json is None:
        raise AppError(
            "request_unresolved",
            "This question is still running or was interrupted. "
            "Check again for its result; it will not be generated again automatically.",
            409,
        )
    result = (existing.id, dict(existing.response_json))
    await db.commit()
    return result


async def claim(
    db: AsyncSession, learner_id: str, key: str, payload: dict[str, Any]
) -> tuple[str, dict[str, Any] | None]:
    fingerprint = request_fingerprint(payload)
    # Close read snapshots before taking the short write lock; no pending writes on entry.
    await db.commit()
    identity = new_id()
    try:
        inserted = await db.scalar(
            insert(AskRequest)
            .values(
                id=identity,
                learner_id=learner_id,
                request_key=key,
                fingerprint=fingerprint,
                response_json=None,
            )
            .on_conflict_do_nothing(index_elements=["learner_id", "request_key"])
            .returning(AskRequest.id)
        )
        if inserted:
            await db.commit()
            return identity, None
        existing = await db.scalar(
            select(AskRequest).where(
                AskRequest.learner_id == learner_id,
                AskRequest.request_key == key,
            )
        )
        assert existing is not None
        if existing.fingerprint != fingerprint:
            raise AppError(
                "request_conflict", "This request identity belongs to a different question.", 409
            )
        if existing.response_json is None:
            raise AppError(
                "request_unresolved",
                "This question is still running or was interrupted. Check again to recover its result; "
                "it will not be generated again automatically.",
                409,
            )
        result = (existing.id, dict(existing.response_json))
        await db.commit()
        return result
    except BaseException:
        await db.rollback()
        raise


async def complete(
    db: AsyncSession, learner_id: str, identity: str, response: dict[str, Any]
) -> None:
    """Caller owns the atomic answer+receipt transaction."""
    updated = await db.scalar(
        update(AskRequest)
        .where(
            AskRequest.id == identity,
            AskRequest.learner_id == learner_id,
        )
        .values(response_json=response)
        .returning(AskRequest.id)
    )
    if updated is None:
        raise AppError("request_unavailable", "This question was removed before it finished.", 410)
