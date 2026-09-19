"""CompetencyState (ADR-0004): a kernel-refreshed view over competency_evidence rows.

Per skill × dimension: time-decayed weighted mean score, evidence count, confidence. The recall
dimension also blends the mean FSRS retrievability of the skill's review items. Mastery is a view
over the node's *required* dimensions with a coverage factor (≥ 2 evidence rows = full coverage),
so one lucky MCQ never unlocks anything. `refresh()` is idempotent and re-runnable.
"""

import math
import statistics
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow_iso
from app.db.events import EventWriter, Verb
from app.db.models import CompetencyEvidence, CompetencyState, SkillNode
from app.kernel import memory
from app.schemas.common import ObjectType

DIMENSIONS = ("recall", "explanation", "application", "transfer")
DIM_WEIGHTS = {"recall": 0.25, "explanation": 0.35, "application": 0.25, "transfer": 0.15}
GRADER_WEIGHT = {"deterministic": 1.0, "rubric": 0.8, "local": 0.7, "hosted": 1.0}
HALF_LIFE_DAYS = 30.0
FULL_COVERAGE_COUNT = 2


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


async def record_evidence(
    db: AsyncSession,
    learner_id: str,
    skill_id: str,
    dimension: str,
    score: float,
    *,
    grader_level: str,
    confidence: float = 1.0,
    attempt_id: str | None = None,
    events: EventWriter | None = None,
) -> CompetencyEvidence:
    if dimension not in DIMENSIONS:
        raise ValueError(f"unknown dimension {dimension}")
    score = min(1.0, max(0.0, score))
    weight = GRADER_WEIGHT.get(grader_level, 0.7) * max(0.1, min(1.0, confidence))
    row = CompetencyEvidence(
        learner_id=learner_id,
        skill_id=skill_id,
        dimension=dimension,
        score=score,
        weight=weight,
        grader_level=grader_level,
        source_attempt_id=attempt_id,
    )
    db.add(row)
    await db.commit()
    if events is not None:
        await events.emit(
            Verb.EVIDENCED,
            ObjectType.NODE,
            skill_id,
            result={"skill_id": skill_id, "dimension": dimension, "score": score, "weight": weight},
            context={"attempt_id": attempt_id},
        )
    return row


def _aggregate(rows: list[CompetencyEvidence], now: datetime) -> tuple[float, int, float] | None:
    if not rows:
        return None
    ws, wsum, scores = 0.0, 0.0, []
    for r in rows:
        age_days = max(0.0, (now - _parse(r.ts)).total_seconds() / 86400)
        w = r.weight * math.pow(0.5, age_days / HALF_LIFE_DAYS)
        ws += w * r.score
        wsum += w
        scores.append(r.score)
    score = ws / wsum if wsum else 0.0
    n = len(rows)
    spread = statistics.pstdev(scores) if n > 1 else 0.5  # unknown agreement with one row
    confidence = (n / (n + 1)) * (1.0 - min(0.5, spread))
    return score, n, confidence


async def refresh(
    db: AsyncSession, learner_id: str, skill_id: str, *, now: datetime | None = None
) -> dict[str, CompetencyState]:
    now = now or datetime.now(UTC)
    stmt = select(CompetencyEvidence).where(
        CompetencyEvidence.learner_id == learner_id, CompetencyEvidence.skill_id == skill_id
    )
    rows = list((await db.execute(stmt)).scalars().all())
    by_dim: dict[str, list[CompetencyEvidence]] = {d: [] for d in DIMENSIONS}
    for r in rows:
        by_dim.setdefault(r.dimension, []).append(r)
    mean_r = await memory.mean_retrievability(db, learner_id, skill_id, now=now)

    existing = {
        s.dimension: s
        for s in (
            await db.execute(
                select(CompetencyState).where(
                    CompetencyState.learner_id == learner_id, CompetencyState.skill_id == skill_id
                )
            )
        ).scalars()
    }
    out: dict[str, CompetencyState] = {}
    for dim in DIMENSIONS:
        agg = _aggregate(by_dim[dim], now)
        if dim == "recall" and mean_r is not None:
            if agg is None:
                agg = (mean_r, 0, 0.3)
            else:
                agg = (0.5 * agg[0] + 0.5 * mean_r, agg[1], agg[2])
        if agg is None:
            if dim in existing:
                await db.execute(
                    delete(CompetencyState).where(CompetencyState.id == existing[dim].id)
                )
            continue
        score, n, conf = agg
        last_ts = max((r.ts for r in by_dim[dim]), default=None)
        state = existing.get(dim)
        if state is None:
            state = CompetencyState(
                learner_id=learner_id,
                skill_id=skill_id,
                dimension=dim,
                score=score,
                count=n,
                confidence=conf,
                last_evidence_ts=last_ts,
            )
            db.add(state)
        else:
            state.score, state.count, state.confidence = score, n, conf
            state.last_evidence_ts = last_ts
            state.refreshed_at = utcnow_iso()
        out[dim] = state
    await db.commit()
    return out


async def states(db: AsyncSession, learner_id: str, skill_id: str) -> dict[str, CompetencyState]:
    stmt = select(CompetencyState).where(
        CompetencyState.learner_id == learner_id, CompetencyState.skill_id == skill_id
    )
    return {s.dimension: s for s in (await db.execute(stmt)).scalars()}


def required_dimensions(node: SkillNode | None) -> list[str]:
    req: Any = (node.assessment_requirements_json or {}).get("dimensions") if node else None
    dims = [d for d in (req or []) if d in DIMENSIONS]
    return dims or ["recall", "explanation"]


def mastery_from_states(states_by_dim: dict[str, CompetencyState], required: list[str]) -> float:
    total = sum(DIM_WEIGHTS[d] for d in required) or 1.0
    acc = 0.0
    for d in required:
        s = states_by_dim.get(d)
        if s is None:
            continue
        coverage = min(1.0, s.count / FULL_COVERAGE_COUNT) if s.count else 0.5
        acc += DIM_WEIGHTS[d] * s.score * coverage
    return round(acc / total, 4)


async def mastery(db: AsyncSession, learner_id: str, skill_id: str) -> float:
    node = await db.get(SkillNode, skill_id)
    return mastery_from_states(await states(db, learner_id, skill_id), required_dimensions(node))


async def skill_state(db: AsyncSession, learner_id: str, skill_id: str) -> dict[str, Any]:
    """Open-learner-model view of one node: per-dimension state + mastery + memory summary."""
    node = await db.get(SkillNode, skill_id)
    st = await states(db, learner_id, skill_id)
    return {
        "skill_id": skill_id,
        "mastery": mastery_from_states(st, required_dimensions(node)),
        "dimensions": {
            d: {"score": round(s.score, 3), "count": s.count, "confidence": round(s.confidence, 3)}
            for d, s in st.items()
        },
        "required_dimensions": required_dimensions(node),
        "memory": await memory.skill_memory_summary(db, learner_id, skill_id),
    }
