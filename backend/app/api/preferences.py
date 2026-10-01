from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import DB, Learner
from app.kernel import preferences

router = APIRouter(prefix="/preferences", tags=["preferences"])


class PrefOut(BaseModel):
    values: dict[str, Any]
    specs: list[dict[str, Any]]


class PrefSet(BaseModel):
    key: str
    value: Any
    origin: str = "explicit"


@router.get(
    "",
    summary="All structured preferences with their specs (defaults filled in)",
    response_model=PrefOut,
)
async def get_all(db: DB, learner: Learner) -> PrefOut:
    return PrefOut(
        values=await preferences.get_all(db, learner.id),
        specs=[p.model_dump() for p in preferences.PREFERENCES.values()],
    )


@router.put(
    "",
    summary="Set one preference (explicit by default; adaptations log an adapted event)",
    response_model=PrefOut,
)
async def set_one(body: PrefSet, db: DB, learner: Learner) -> PrefOut:
    await preferences.set_pref(db, learner.id, body.key, body.value, origin=body.origin)
    return await get_all(db, learner)


@router.delete("/{key}", summary="Reset one preference to its default", response_model=PrefOut)
async def reset(key: str, db: DB, learner: Learner) -> PrefOut:
    await preferences.reset(db, learner.id, key)
    return await get_all(db, learner)
