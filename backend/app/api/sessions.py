from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import DB, Learner
from app.db.models import Session
from app.kernel import memory, skill_graph
from app.kernel import session as ksession
from app.schemas.common import Mode
from app.schemas.tutor import SkillView

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionStart(BaseModel):
    mode: Mode = Mode.STEADY
    energy: int = Field(ge=1, le=5, default=3)
    socratic: bool = False


class SessionEnd(BaseModel):
    energy_after: int = Field(ge=1, le=5)
    self_report: int = Field(ge=1, le=5)
    notes: str | None = None


class SessionOut(BaseModel):
    id: str
    mode: str
    energy: int
    socratic: bool
    started_at: str
    ended_at: str | None
    energy_after: int | None
    next_skill: SkillView | None
    due_reviews: int
    review_cap: int
    minimum_viable: list[str]


async def _out(db: DB, learner_id: str, s: Session) -> SessionOut:
    from app.api.skills import _view

    nxt = await skill_graph.next_skill(db, learner_id)
    cap = memory.review_cap(s.mode, s.energy)
    due = await memory.due_items(db, learner_id, now=datetime.now(UTC), cap=100)
    minimum = (
        ["retrieval", "recap"]
        if s.mode == "low_capacity" or s.energy <= 2
        else ["retrieval", "new_material", "recap"]
    )
    return SessionOut(
        id=s.id,
        mode=s.mode,
        energy=s.energy,
        socratic=s.socratic,
        started_at=s.started_at,
        ended_at=s.ended_at,
        energy_after=s.energy_after,
        next_skill=await _view(db, learner_id, nxt) if nxt else None,
        due_reviews=len(due),
        review_cap=cap,
        minimum_viable=minimum,
    )


@router.post(
    "",
    summary="Start a session (learner-chosen mode + energy)",
    response_model=SessionOut,
    status_code=201,
)
async def start(body: SessionStart, db: DB, learner: Learner) -> SessionOut:
    s = await ksession.start(
        db, learner.id, mode=body.mode, energy=body.energy, socratic=body.socratic
    )
    return await _out(db, learner.id, s)


@router.get("/{session_id}", summary="Session state", response_model=SessionOut)
async def get(session_id: str, db: DB, learner: Learner) -> SessionOut:
    return await _out(db, learner.id, await ksession.get(db, session_id))


@router.post(
    "/{session_id}/end", summary="End with confidence-rated recap", response_model=SessionOut
)
async def end(session_id: str, body: SessionEnd, db: DB, learner: Learner) -> SessionOut:
    s = await ksession.end(
        db,
        session_id,
        energy_after=body.energy_after,
        self_report=body.self_report,
        notes=body.notes,
    )
    return await _out(db, learner.id, s)
