from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DB, Learner
from app.api.plan import build_plan, plan_to_json
from app.db.models import Assessment, ReviewItem, Session
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
    plan: list[dict[str, Any]]
    checkpoint: dict[str, Any] | None


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
        plan=list(s.planned_blocks_json or []),
        checkpoint=await ksession.load_checkpoint(db, s.id),
    )


@router.post(
    "",
    summary="Start a session (learner-chosen mode + energy)",
    response_model=SessionOut,
    status_code=201,
)
async def start(body: SessionStart, db: DB, learner: Learner) -> SessionOut:
    plan = await build_plan(db, learner.id, str(body.mode), body.energy)
    s = await ksession.start(
        db,
        learner.id,
        mode=body.mode,
        energy=body.energy,
        socratic=body.socratic,
        planned_blocks=[b.type for b in plan.blocks],
    )
    s.planned_blocks_json = plan_to_json(plan)
    await db.commit()
    return await _out(db, learner.id, s)


@router.get(
    "/current",
    summary="The latest session that has not ended (for resume after reload)",
    response_model=SessionOut | None,
)
async def current(db: DB, learner: Learner) -> SessionOut | None:
    stmt = (
        select(Session)
        .where(Session.learner_id == learner.id, Session.ended_at.is_(None))
        .order_by(Session.started_at.desc())
        .limit(1)
    )
    s = (await db.execute(stmt)).scalar_one_or_none()
    return await _out(db, learner.id, s) if s else None


class CheckpointIn(BaseModel):
    phase: str | None = None
    skill_id: str | None = None
    block_index: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/{session_id}/checkpoint",
    summary="Merge UI state (phase, skill, block) into the resume checkpoint",
    response_model=dict[str, Any],
)
async def checkpoint(session_id: str, body: CheckpointIn, db: DB) -> dict[str, Any]:
    s = await ksession.get(db, session_id)
    cp = await ksession.load_checkpoint(db, s.id) or {}
    update = {
        k: v
        for k, v in (
            ("phase", body.phase),
            ("skill_id", body.skill_id),
            ("block_index", body.block_index),
        )
        if v is not None
    }
    merged = {**cp, **update, **body.extra}
    await ksession.save_checkpoint(db, s, merged)
    await ksession.prune_checkpoints(db, s.id, keep=3)
    return merged


@router.get("/{session_id}", summary="Session state", response_model=SessionOut)
async def get(session_id: str, db: DB, learner: Learner) -> SessionOut:
    return await _out(db, learner.id, await ksession.get(db, session_id))


@router.post(
    "/{session_id}/end", summary="End with confidence-rated recap", response_model=SessionOut
)
async def end(session_id: str, body: SessionEnd, db: DB, learner: Learner) -> SessionOut:
    await ensure_recall_item_for_explained_skill(db, learner.id, session_id)
    await ksession.prune_checkpoints(db, session_id)
    s = await ksession.end(
        db,
        session_id,
        energy_after=body.energy_after,
        self_report=body.self_report,
        notes=body.notes,
    )
    return await _out(db, learner.id, s)


async def ensure_recall_item_for_explained_skill(db: DB, learner_id: str, session_id: str) -> None:
    """Pedagogy guardrail: any explain flow ends with a recall item in FSRS. If the session's skill has
    no review items yet, schedule its first assessment (due now) so the queue is never empty."""
    cp = await ksession.load_checkpoint(db, session_id) or {}
    skill_id = cp.get("skill_id")
    if not skill_id:
        return
    has = (
        await db.execute(
            select(ReviewItem.id)
            .where(ReviewItem.learner_id == learner_id, ReviewItem.skill_id == skill_id)
            .limit(1)
        )
    ).first()
    if has:
        return
    first = (
        await db.execute(
            select(Assessment)
            .where(Assessment.skill_id == skill_id)
            .order_by(Assessment.kind)
            .limit(1)
        )
    ).scalar_one_or_none()
    if first is not None:
        await memory.ensure_item(
            db, learner_id, skill_id, first.kind, {"ref": first.id, "assessment_id": first.id}
        )
