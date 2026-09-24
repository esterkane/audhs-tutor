from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DB, Learner
from app.api.plan import build_plan, plan_to_json, session_lock
from app.core.errors import AppError
from app.db import models
from app.db.models import Assessment, ReviewItem, Session
from app.kernel import adaptation, blocks, experiments, memory, skill_graph
from app.kernel import session as ksession
from app.schemas.common import Mode
from app.schemas.tutor import SkillView

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionStart(BaseModel):
    mode: Mode = Mode.STEADY
    energy: int = Field(ge=1, le=5, default=3)
    socratic: bool = False
    skill_id: str | None = None  # explicit saved-lesson choice, independent of the default goal


class SessionEnd(BaseModel):
    energy_after: int | None = Field(default=None, ge=1, le=5)
    self_report: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None


class SessionOut(BaseModel):
    id: str
    mode: str
    energy: int
    socratic: bool
    started_at: str
    ended_at: str | None
    energy_after: int | None
    next_skill: SkillView | None  # the map's recommendation (may move after a grade)
    active_skill: SkillView | None = None  # the skill this session is working on (persisted)
    due_reviews: int
    review_cap: int
    minimum_viable: list[str]
    plan: list[dict[str, Any]]
    checkpoint: dict[str, Any] | None
    state: blocks.BlockState  # server-authoritative block / phase / active skill
    experiment: dict[str, Any] | None = None  # {id, name, arm, config, unit_type} when running


async def _experiment_info(db: DB, learner_id: str, s: Session) -> dict[str, Any] | None:
    if s.experiment_arm_id:
        arm = await db.get(models.ExperimentArm, s.experiment_arm_id)
        if arm is not None:
            exp = await db.get(models.Experiment, arm.experiment_id)
            if exp is not None:
                return {
                    "id": exp.id,
                    "name": exp.name,
                    "arm": arm.name,
                    "config": dict(arm.config_json),
                    "unit_type": "session",
                }
    for exp in await experiments.running(db, learner_id, unit_type="node"):
        return {"id": exp.id, "name": exp.name, "arm": None, "config": {}, "unit_type": "node"}
    return None


async def _out(db: DB, learner_id: str, s: Session) -> SessionOut:
    from app.api.skills import _view

    nxt = await skill_graph.next_skill(db, learner_id)
    st = await blocks.state(db, s)
    active = await skill_graph.get_node(db, st.skill_id) if st.skill_id else None
    cap = memory.review_cap(s.mode, s.energy)
    cp = await ksession.load_checkpoint(db, s.id) or {}
    due = await memory.due_items(
        db,
        learner_id,
        now=datetime.now(UTC),
        cap=100,
        exclude_domains=("language",),
        skill_ids=cp.get("scope_skill_ids"),
    )
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
        active_skill=await _view(db, learner_id, active) if active else None,
        due_reviews=len(due),
        review_cap=cap,
        minimum_viable=minimum,
        plan=list(s.planned_blocks_json or []),
        checkpoint=await ksession.load_checkpoint(db, s.id),
        state=st,
        experiment=await _experiment_info(db, learner_id, s),
    )


@router.post(
    "",
    summary="Start a session (learner-chosen mode + energy)",
    response_model=SessionOut,
    status_code=201,
)
async def start(body: SessionStart, db: DB, learner: Learner) -> SessionOut:
    chosen = await skill_graph.selection(db, learner.id, body.skill_id)
    nxt, scope = chosen
    if scope is not None and nxt is None:
        raise AppError(
            "no_active_lesson",
            "No available lesson in this selection. Review and activate a draft in Learning areas first.",
            http_status=409,
        )
    s = await ksession.start(
        db, learner.id, mode=body.mode, energy=body.energy, socratic=body.socratic, emit=False
    )
    # 1. 'Try' adaptations last one session: revert earlier trials *before* planning this one
    await adaptation.expire_trials(db, learner.id, current_session=s)
    # 2. a running session-unit experiment assigns an arm (may set socratic / block lengths)
    arm_pair = await experiments.arm_for_session(db, learner.id, s)
    overrides = dict(arm_pair[1].config_json) if arm_pair else None
    # 3. plan with the learner's preferences (+ the arm's overrides, disclosed in SessionOut)
    plan = await build_plan(
        db,
        learner.id,
        str(body.mode),
        body.energy,
        overrides=overrides,
        selection=chosen,
    )
    s.planned_blocks_json = plan_to_json(plan)
    await db.commit()
    # the active skill is persisted here; `next_skill` stays a recommendation that may change
    await ksession.save_checkpoint(
        db,
        s,
        {
            "skill_id": nxt.id if nxt else None,
            "plan_version": 1,
            "block_status": None,
            "scope_skill_ids": scope,
        },
    )
    await ksession.emit_started(db, s, [b.type for b in plan.blocks])
    # 4. look for patterns worth a card
    await adaptation.observe(db, learner.id, session=s)
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
    block_index: int | None = Field(
        default=None, description="must equal the running block; the client cannot move blocks"
    )
    extra: dict[str, Any] = Field(default_factory=dict)


# owned by kernel/blocks.py: a UI checkpoint can never rewrite them (server authority)
RESERVED_CHECKPOINT_KEYS = frozenset(
    {
        "block_index",
        "block_id",
        "block_type",
        "block_status",
        "block_started_at",
        "plan_version",
        "timer_extension_min",
        "first_started_index",
        "scope_skill_ids",
    }
)
SUB_PHASES = {"new_material": {"teach", "assess"}}


@router.post(
    "/{session_id}/checkpoint",
    summary="Merge UI state (sub-phase, skill) into the resume checkpoint; block fields are server-owned",
    response_model=dict[str, Any],
)
async def checkpoint(
    session_id: str, body: CheckpointIn, request: Request, db: DB
) -> dict[str, Any]:
    s = await ksession.get(db, session_id)
    async with session_lock(request, session_id):
        cp = await ksession.load_checkpoint(db, s.id) or {}
        current = cp.get("block_index") if cp.get("block_status") == "running" else None
        if body.block_index is not None and current is not None and body.block_index != current:
            raise AppError(
                "stale_block",
                f"block {current} is running; a checkpoint for block {body.block_index} is stale",
                http_status=409,
            )
        update: dict[str, Any] = {}
        if body.phase is not None:
            block_type = str(cp.get("block_type") or "")
            allowed = SUB_PHASES.get(
                block_type, {blocks.phase_for(block_type)} if block_type else None
            )
            if current is not None and allowed is not None and body.phase not in allowed:
                raise AppError(
                    "invalid_phase",
                    f"phase {body.phase!r} is not valid inside a {block_type} block",
                    http_status=409,
                )
            update["phase"] = body.phase
        if body.skill_id is not None:
            update["skill_id"] = body.skill_id
        extra = {k: v for k, v in body.extra.items() if k not in RESERVED_CHECKPOINT_KEYS}
        merged = {**cp, **extra, **update}
        await ksession.save_checkpoint(db, s, merged)
    return merged


@router.get("/{session_id}", summary="Session state", response_model=SessionOut)
async def get(session_id: str, db: DB, learner: Learner) -> SessionOut:
    return await _out(db, learner.id, await ksession.get(db, session_id))


@router.post(
    "/{session_id}/end",
    summary="End a session; recap ratings are optional",
    response_model=SessionOut,
)
async def end(
    session_id: str, body: SessionEnd, request: Request, db: DB, learner: Learner
) -> SessionOut:
    async with session_lock(request, session_id):
        return await _end_session(session_id, body, db, learner)


async def _end_session(session_id: str, body: SessionEnd, db: DB, learner: Learner) -> SessionOut:
    await ensure_recall_item_for_explained_skill(db, learner.id, session_id)
    await blocks.end_running(db, await ksession.get(db, session_id), reason="session_end")
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
    explained = (
        await db.execute(
            select(models.LearningEvent).where(
                models.LearningEvent.learner_id == learner_id,
                models.LearningEvent.session_id == session_id,
                models.LearningEvent.verb == "explained",
            )
        )
    ).scalars()
    if not any(
        (event.context_json or {}).get("node_id") == skill_id
        and int((event.result_json or {}).get("sentences") or 0) > 0
        for event in explained
    ):
        return  # stopping before an explanation must not create an unseen recall card
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
            .where(Assessment.skill_id == skill_id, Assessment.kind != "code")
            .order_by(Assessment.kind)
            .limit(1)
        )
    ).scalar_one_or_none()
    if first is not None:
        await memory.ensure_item(
            db, learner_id, skill_id, first.kind, {"ref": first.id, "assessment_id": first.id}
        )
