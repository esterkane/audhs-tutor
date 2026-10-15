"""Adaptation cards: observe patterns → propose → learner decides → undo. Never silent."""

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, Learner
from app.db.models import Adaptation, Session
from app.kernel import adaptation, plan_versions, planner
from app.kernel import session as ksession
from app.schemas.adaptation import DecideIn, HistoryList, HistoryOut, ProposalList, ProposalOut

router = APIRouter(prefix="/adaptations", tags=["adaptations"])


async def _proposal(db: AsyncSession, a: Adaptation) -> ProposalOut:
    return ProposalOut(
        id=a.id,
        what=a.what,
        why=a.why,
        origin=a.origin,
        pattern=a.pattern,
        pref=str(a.apply_json.get("pref", "")),
        value=a.apply_json.get("value"),
        evidence=dict(a.evidence_json or {}),
        proposed_at=a.proposed_at,
        reversible=a.reversible,
        session_id=a.session_id,
        plan_blocks=[
            planner.Block.model_validate(b) for b in a.apply_json.get("value", {}).get("blocks", [])
        ]
        if a.apply_json.get("pref") == "session.plan"
        else [],
        protected_blocks=plan_versions.protected_count(a.evidence_json.get("plan_binding") or {}),
        plan_state=await adaptation.plan_state(db, a),
    )


async def _session(db: AsyncSession, session_id: str | None, learner_id: str) -> Session | None:
    return await ksession.get_owned(db, session_id, learner_id) if session_id else None


@router.get("", summary="Open proposal cards", response_model=ProposalList)
async def pending(db: DB, learner: Learner) -> ProposalList:
    return ProposalList(
        proposals=[await _proposal(db, a) for a in await adaptation.pending(db, learner.id)]
    )


@router.post(
    "/observe",
    summary="Run the pattern rules now and return the open cards",
    response_model=ProposalList,
)
async def observe(db: DB, learner: Learner, session_id: str | None = None) -> ProposalList:
    cards = await adaptation.observe(
        db, learner.id, session=await _session(db, session_id, learner.id)
    )
    return ProposalList(proposals=[await _proposal(db, a) for a in cards])


@router.post(
    "/{adaptation_id}/decide",
    summary="Try (this session) / Make default / No (ask in 14 days) / Don't suggest again",
    response_model=HistoryList,
)
async def decide(adaptation_id: str, body: DecideIn, db: DB, learner: Learner) -> HistoryList:
    await adaptation.decide(
        db,
        learner.id,
        adaptation_id,
        body.decision,
        session=await _session(db, body.session_id, learner.id),
    )
    return await log(db, learner)


@router.post(
    "/{adaptation_id}/undo",
    summary="Revert an applied adaptation to the previous value (logged as undone)",
    response_model=HistoryList,
)
async def undo(adaptation_id: str, db: DB, learner: Learner) -> HistoryList:
    await adaptation.undo(db, learner.id, adaptation_id)
    return await log(db, learner)


@router.get(
    "/log", summary="Adaptation log: every card and what happened to it", response_model=HistoryList
)
async def log(db: DB, learner: Learner) -> HistoryList:
    entries = []
    for h in await adaptation.history(db, learner.id):
        a = h.adaptation
        entries.append(
            HistoryOut(
                id=a.id,
                what=a.what,
                why=a.why,
                origin=a.origin,
                pattern=a.pattern,
                pref=str(a.apply_json.get("pref", "")),
                value=a.apply_json.get("value"),
                previous=(a.previous_json or {}).get("value"),
                proposed_at=a.proposed_at,
                decision=h.decision,
                decided_at=h.decided_at,
                undone_at=h.undone_at,
                in_effect=h.in_effect,
                trial=a.session_id is not None,
                plan_state=await adaptation.plan_state(db, a, undo=h.in_effect),
            )
        )
    return HistoryList(entries=entries)


@router.post("/{adaptation_id}/refresh-plan", response_model=ProposalOut)
async def refresh_plan(adaptation_id: str, db: DB, learner: Learner) -> ProposalOut:
    return await _proposal(db, await adaptation.refresh_plan(db, learner.id, adaptation_id))
