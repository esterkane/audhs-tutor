"""Explicit curated-reference downloads/imports; status reads never access the network."""

import asyncio

from fastapi import APIRouter, Request

from app.api.deps import DB, Learner, Repo, SettingsDep
from app.knowledge import references
from app.schemas.references import (
    ReferenceImport,
    ReferenceImported,
    ReferenceLoad,
    ReferenceSnapshot,
    ReferenceStatus,
)

router = APIRouter(prefix="/references", tags=["references"])


def lock(request: Request, identity: str) -> asyncio.Lock:
    references.card(identity)
    if not hasattr(request.app.state, "reference_locks"):
        request.app.state.reference_locks = {}
    locks: dict[str, asyncio.Lock] = request.app.state.reference_locks
    if identity not in locks:
        locks[identity] = asyncio.Lock()
    return locks[identity]


@router.get(
    "/{identity}",
    response_model=ReferenceStatus,
    summary="Read local reference-copy status without fetching",
)
async def status(identity: str, learner: Learner, settings: SettingsDep) -> ReferenceStatus:
    return ReferenceStatus(
        snapshot=references.current(settings.reference_cache_dir_resolved, identity)
    )


@router.post(
    "/{identity}/load",
    response_model=ReferenceSnapshot,
    summary="Explicitly save or refresh a curated external page locally",
)
async def load(
    identity: str, body: ReferenceLoad, request: Request, learner: Learner, settings: SettingsDep
) -> ReferenceSnapshot:
    async with lock(request, identity):
        return await references.load(
            settings.reference_cache_dir_resolved, identity, refresh=body.refresh
        )


@router.post(
    "/{identity}/import",
    response_model=ReferenceImported,
    summary="Explicitly import a saved reading copy into the local library",
)
async def import_copy(
    identity: str,
    body: ReferenceImport,
    request: Request,
    db: DB,
    repo: Repo,
    learner: Learner,
    settings: SettingsDep,
) -> ReferenceImported:
    async with lock(request, identity):
        return await references.import_copy(
            db, repo, settings.reference_cache_dir_resolved, identity, body.snapshot_id
        )
