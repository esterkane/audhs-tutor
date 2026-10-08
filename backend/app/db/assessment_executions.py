"""Assessment-only durable staging, never a claim-reclaim mechanism.

Short-transaction methods require no pending caller writes. JSON semantics are
validated by the orchestrator; store no corpus passages or hidden answer keys.
"""

from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow_iso
from app.db.models import AssessmentExecution, WorkspaceRequest


def _conflict() -> AppError:
    return AppError("execution_conflict", "This execution cannot make that transition.", 409)


async def get_owned(db: AsyncSession, learner_id: str, claim_id: str) -> AssessmentExecution | None:
    return cast(
        AssessmentExecution | None,
        await db.scalar(
            select(AssessmentExecution)
            .join(WorkspaceRequest, WorkspaceRequest.id == AssessmentExecution.claim_id)
            .where(
                AssessmentExecution.claim_id == claim_id,
                AssessmentExecution.learner_id == learner_id,
                WorkspaceRequest.learner_id == learner_id,
                WorkspaceRequest.request_key.startswith("assessment:"),
            )
            .execution_options(populate_existing=True)
        ),
    )


async def _lock(db: AsyncSession, learner_id: str, claim_id: str) -> WorkspaceRequest:
    await db.execute(
        update(WorkspaceRequest)
        .where(WorkspaceRequest.id == claim_id, WorkspaceRequest.learner_id == learner_id)
        .values(fingerprint=WorkspaceRequest.fingerprint)
    )
    claim = await db.scalar(
        select(WorkspaceRequest)
        .where(WorkspaceRequest.id == claim_id, WorkspaceRequest.learner_id == learner_id)
        .execution_options(populate_existing=True)
    )
    if claim is None or not claim.request_key.startswith("assessment:"):
        raise AppError("not_found", "Assessment request not found.", 404)
    return claim


async def prepare(
    db: AsyncSession,
    learner_id: str,
    claim_id: str,
    *,
    request_json: dict[str, Any],
    content_fingerprint: str,
    owner_json: dict[str, Any] | None = None,
) -> None:
    """Only the invocation that just created the claim may call this method."""
    if not request_json or not content_fingerprint:
        raise ValueError("Request and content fingerprint are required")
    await db.commit()
    try:
        claim = await _lock(db, learner_id, claim_id)
        if claim.response_json is not None or await get_owned(db, learner_id, claim_id) is not None:
            raise _conflict()
        db.add(
            AssessmentExecution(
                claim_id=claim_id,
                learner_id=learner_id,
                schema_version=1,
                phase="prepared",
                content_fingerprint=content_fingerprint,
                request_json=request_json,
                grade_json=None,
                owner_json=owner_json,
            )
        )
        await db.commit()
    except BaseException:
        await db.rollback()
        raise


async def mark_inference_started(db: AsyncSession, learner_id: str, claim_id: str) -> None:
    """Durably mark the irreversible boundary BEFORE entering the gateway."""
    await db.commit()
    try:
        claim = await _lock(db, learner_id, claim_id)
        row = await get_owned(db, learner_id, claim_id)
        if (
            row is None
            or row.schema_version != 1
            or row.phase != "prepared"
            or claim.response_json is not None
        ):
            raise _conflict()
        row.phase = "inference_started"
        row.updated_at = utcnow_iso()
        await db.commit()
    except BaseException:
        await db.rollback()
        raise


async def save_grade(
    db: AsyncSession, learner_id: str, claim_id: str, *, grade_json: dict[str, Any]
) -> None:
    """Persist an orchestrator-validated payload; never replace a staged result."""
    if not grade_json:
        raise ValueError("Validated grade payload is required")
    await db.commit()
    try:
        claim = await _lock(db, learner_id, claim_id)
        row = await get_owned(db, learner_id, claim_id)
        if row is None or row.schema_version != 1 or claim.response_json is not None:
            raise _conflict()
        if row.phase == "grade_ready" and row.grade_json == grade_json:
            await db.commit()
            return
        if row.phase not in ("prepared", "inference_started"):
            raise _conflict()
        row.grade_json = grade_json
        row.phase = "grade_ready"
        row.updated_at = utcnow_iso()
        await db.commit()
    except BaseException:
        await db.rollback()
        raise


async def mark_completed(db: AsyncSession, learner_id: str, claim_id: str) -> None:
    """Flush only, within caller's atomic learning/outcome transaction."""
    claim = await _lock(db, learner_id, claim_id)
    row = await get_owned(db, learner_id, claim_id)
    if (
        row is None
        or row.schema_version != 1
        or row.phase != "grade_ready"
        or claim.response_json is None
    ):
        raise _conflict()
    row.phase = "completed"
    row.updated_at = utcnow_iso()
    await db.flush()


async def lock_prepared(
    db: AsyncSession, learner_id: str, claim_id: str, owner_json: dict[str, Any]
) -> tuple[WorkspaceRequest, AssessmentExecution]:
    """Recheck under a short write lock while caller holds verified external ownership.

    Caller validates session/request/content and commits or rolls back before inference.
    This never changes execution phase or creates a missing claim.
    """
    claim = await _lock(db, learner_id, claim_id)
    row = await get_owned(db, learner_id, claim_id)
    if (
        row is None
        or row.schema_version != 1
        or row.phase != "prepared"
        or row.owner_json != owner_json
        or claim.response_json is not None
    ):
        raise _conflict()
    return claim, row
