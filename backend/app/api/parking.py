from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DB, Learner
from app.db.events import EventWriter
from app.db.models import ParkingLotItem
from app.kernel import session as ksession
from app.orchestrator.tools import park_tangent

router = APIRouter(prefix="/parking", tags=["parking"])


class ParkIn(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=500)
    node_id: str | None = None


class ParkOut(BaseModel):
    id: str
    text: str
    node_id: str | None
    status: str
    created_at: str


class ParkList(BaseModel):
    items: list[ParkOut]


def _out(p: ParkingLotItem) -> ParkOut:
    return ParkOut(
        id=p.id, text=p.text, node_id=p.node_id, status=p.status, created_at=p.created_at
    )


@router.post(
    "",
    summary="Park a tangent (≤ 2 interactions, linked to the current node)",
    response_model=ParkOut,
    status_code=201,
)
async def park(body: ParkIn, db: DB) -> ParkOut:
    s = await ksession.get(db, body.session_id)
    events = EventWriter(db, ksession.event_context(s))
    return _out(await park_tangent(db, s, body.text, node_id=body.node_id, events=events))


@router.get("", summary="Parked items", response_model=ParkList)
async def list_parked(db: DB, learner: Learner, status: str = Query("parked")) -> ParkList:
    stmt = (
        select(ParkingLotItem)
        .where(ParkingLotItem.learner_id == learner.id, ParkingLotItem.status == status)
        .order_by(ParkingLotItem.created_at.desc())
    )
    return ParkList(items=[_out(p) for p in (await db.execute(stmt)).scalars()])
