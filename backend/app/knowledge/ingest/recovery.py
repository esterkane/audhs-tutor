"""Conservative recovery of imports whose same-host worker ownership can be disproved."""

from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.base import utcnow_iso
from app.db.models import IngestRun
from app.knowledge.ingest.ownership import OwnershipUnavailable, RunOwnership

OWNER_KEY = "_local_owner_v2"


def database_path(db: AsyncSession) -> Path:
    url = db.get_bind().engine.url
    if (
        url.get_backend_name() != "sqlite"
        or not url.database
        or url.database == ":memory:"
        or url.query
    ):
        raise OwnershipUnavailable("Ownership requires a local file-backed SQLite database")
    return Path(url.database)


def acquire_new_owner(db: AsyncSession, run_id: str) -> RunOwnership | None:
    try:
        return RunOwnership.acquire(database_path(db), run_id, create=True)
    except OwnershipUnavailable:
        # Existing ingest remains available, but this run has no automatic recovery proof.
        return None


def owner_marker(owner: RunOwnership | None) -> dict[str, Any]:
    return {OWNER_KEY: [*owner.identity, owner.nonce]} if owner is not None else {}


async def reconcile_abandoned_runs(factory: async_sessionmaker[AsyncSession]) -> int:
    """Dedicated sessions; never borrow a caller's transaction or infer death from age.

    Legacy/missing/unsafe ownership evidence remains unknown. No model/index/file import
    is executed. The compare-and-set rechecks the durable status while holding ownership.
    """
    async with factory() as db:
        try:
            path = database_path(db)
        except OwnershipUnavailable:
            return 0
        candidates = (
            await db.execute(
                select(IngestRun.id, IngestRun.options_json).where(
                    IngestRun.status == "running",
                )
            )
        ).all()
    recovered = 0
    for run_id, options in candidates:
        marker = options.get(OWNER_KEY)
        if (
            not isinstance(marker, list)
            or len(marker) != 3
            or any(type(v) is not int for v in marker[:2])
            or not isinstance(marker[2], str)
        ):
            continue
        try:
            owner = RunOwnership.acquire(
                path, run_id, expected=(marker[0], marker[1]), expected_nonce=marker[2]
            )
        except OwnershipUnavailable:
            continue
        if owner is None:
            continue
        with owner:
            async with factory() as db:
                result = await db.execute(
                    update(IngestRun)
                    .where(
                        IngestRun.id == run_id,
                        IngestRun.status == "running",
                        IngestRun.options_json == options,
                    )
                    .values(status="interrupted", finished_at=utcnow_iso())
                    .returning(IngestRun.id)
                )
                changed = result.scalar_one_or_none() is not None
                await db.commit()
                recovered += int(changed)
    return recovered
