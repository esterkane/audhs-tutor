"""Durable workspace request claims. No model work inside a claim transaction."""

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import new_id
from app.db.models import WorkspaceRequest
from app.kernel.session import get_owned


async def claim(
    db: AsyncSession,
    learner_id: str,
    session_id: str,
    key: str,
    payload: dict[str, Any],
    *,
    validate_new: Callable[[], Awaitable[None]] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    # Only content-validated assessment/review claims need the extra serialized decision.
    # Close the caller's read transaction before acquiring SQLite's write lock:
    # upgrading an older WAL snapshot can fail immediately with SQLITE_BUSY.
    try:
        if validate_new is not None:
            await db.commit()
            await db.execute(
                update(WorkspaceRequest)
                .where(
                    WorkspaceRequest.learner_id == learner_id,
                    WorkspaceRequest.request_key == key,
                )
                .values(fingerprint=WorkspaceRequest.fingerprint)
            )
        return await _claim_locked(
            db, learner_id, session_id, key, payload, validate_new=validate_new
        )
    except BaseException:
        await db.rollback()
        raise


async def _claim_locked(
    db: AsyncSession,
    learner_id: str,
    session_id: str,
    key: str,
    payload: dict[str, Any],
    *,
    validate_new: Callable[[], Awaitable[None]] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Return a new claim id or the original reply; an uncertain claim never runs twice."""
    session = await get_owned(db, session_id, learner_id)
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    existing = await db.scalar(
        select(WorkspaceRequest).where(
            WorkspaceRequest.learner_id == learner_id, WorkspaceRequest.request_key == key
        )
    )
    if existing is None:
        if session.ended_at:
            raise AppError("not_found", "Start or resume a session to use the tutor.", 404)
        if validate_new is not None:
            await validate_new()
        identity = new_id()
        inserted = await db.scalar(
            insert(WorkspaceRequest)
            .values(
                id=identity,
                learner_id=learner_id,
                session_id=session_id,
                request_key=key,
                fingerprint=fingerprint,
                response_json=None,
            )
            .on_conflict_do_nothing(index_elements=["learner_id", "request_key"])
            .returning(WorkspaceRequest.id)
        )
        await db.commit()
        if inserted:
            return identity, None
        existing = await db.scalar(
            select(WorkspaceRequest).where(
                WorkspaceRequest.learner_id == learner_id, WorkspaceRequest.request_key == key
            )
        )
    assert existing is not None
    if existing.fingerprint != fingerprint:
        raise AppError("request_conflict", "This request identity belongs to different work.", 409)
    if existing.response_json is None:
        raise AppError(
            "request_unresolved",
            "This request is still running or was interrupted. Retry to check for its result; "
            "the tutor will not generate it again automatically.",
            409,
        )
    response = dict(existing.response_json)
    identity = existing.id
    await db.commit()
    return identity, response


async def complete(
    db: AsyncSession,
    learner_id: str,
    identity: str,
    response: dict[str, Any],
    *,
    commit: bool = True,
) -> None:
    """Finalize only the already-owned claim; never recreate deleted requests."""
    result = await db.execute(
        update(WorkspaceRequest)
        .where(WorkspaceRequest.id == identity, WorkspaceRequest.learner_id == learner_id)
        .values(response_json=response)
        .returning(WorkspaceRequest.id)
    )
    if result.scalar_one_or_none() is None:
        await db.rollback()
        raise AppError("request_unavailable", "This request was removed before it completed.", 410)
    if commit:
        await db.commit()
    else:
        await db.flush()
