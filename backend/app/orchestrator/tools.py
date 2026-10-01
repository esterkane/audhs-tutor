"""Typed kernel tools for the orchestrator (ARCHITECTURE §2). Deterministic wrappers only."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventWriter, Verb
from app.db.models import LearnerPreference, ParkingLotItem, Session, SkillNode
from app.kernel import competency, skill_graph
from app.knowledge.repository import RetrievalRepository, SearchFilters, SearchResult
from app.schemas.common import ObjectType

TUTOR_MIN_TRUST = 1  # tier 0 (untrusted) never leaves the index for a tutor turn


MIN_HITS = 2  # fewer than this and the search widens one step


async def retrieve(
    repo: RetrievalRepository,
    query: str,
    *,
    skill_id: str | None,
    course: str | None = None,
    k: int = 6,
    min_trust: int = TUTOR_MIN_TRUST,
) -> SearchResult:
    """Skill-filtered search first; when the node has too little material, widen to the skill's
    *course* before the whole corpus — a lesson published from a course is taught from that course
    (the first rehearsal cited another course's notebooks for a course lesson, 2026-09-23). The
    trace records how far the search widened."""
    res = await repo.search(
        query,
        SearchFilters(skill_ids=[skill_id] if skill_id else None, min_trust_tier=min_trust),
        k=k,
    )
    if len(res.hits) >= MIN_HITS or not skill_id:
        return res
    steps: list[tuple[str, SearchFilters]] = []
    if course:
        steps.append(("course", SearchFilters(course=course, min_trust_tier=min_trust)))
    steps.append(("corpus", SearchFilters(min_trust_tier=min_trust)))
    merged = list(res.hits)
    trace = res.trace
    widened: list[str] = []
    for label, filters in steps:
        wide = await repo.search(query, filters, k=k)
        seen = {h.chunk.id for h in merged}
        merged += [h for h in wide.hits if h.chunk.id not in seen]
        trace = wide.trace
        widened.append(label)
        if len(merged) >= MIN_HITS:
            break
    for rank, h in enumerate(merged[:k]):
        h.rank = rank
    trace = trace.model_copy(
        update={
            "chunk_ids": [h.chunk.id for h in merged[:k]],
            "filters": {"skill_ids": [skill_id], "course": course, "widened": widened},
        }
    )
    return SearchResult(hits=merged[:k], trace=trace)


async def get_learning_contract(db: AsyncSession, node: SkillNode) -> dict[str, Any]:
    lo = await skill_graph.learning_object_for(db, node.id)
    prereqs = [p.title for p in await skill_graph.prerequisites(db, node.id)]
    return {
        "skill": node.title,
        "objective": lo.goal if lo else node.description,
        "concept": lo.concept if lo else node.title,
        "success_criteria": node.success_criteria_json,
        "prerequisites": prereqs,
        "examples": (lo.examples_json if lo else [])[:2],
    }


async def get_evidence(db: AsyncSession, learner_id: str, node: SkillNode) -> dict[str, Any]:
    state = await competency.skill_state(db, learner_id, node.id)
    mastered = []
    for n in await skill_graph.all_nodes(db, node.domain):
        if (
            n.id != node.id
            and await competency.mastery(db, learner_id, n.id) >= skill_graph.MASTERY_DONE
        ):
            mastered.append(n.title)
    return {
        "mastery": state["mastery"],
        "dimensions": state["dimensions"],
        "memory": state["memory"],
        "mastered_nodes": mastered[:8],
        "misconceptions": [],
    }


async def get_preferences(db: AsyncSession, learner_id: str) -> dict[str, Any]:
    stmt = select(LearnerPreference).where(LearnerPreference.learner_id == learner_id)
    return {
        p.key: p.value_json
        for p in (await db.execute(stmt)).scalars()
        if not p.key.startswith("routing.")
    }


def session_state(
    session: Session,
    node: SkillNode,
    *,
    block_type: str,
    hint_level: int,
    socratic: bool | None = None,
) -> dict[str, Any]:
    socratic = session.socratic if socratic is None else socratic
    return {
        "mode": session.mode,
        "energy": session.energy,
        "questioning_style": "socratic" if socratic else "explicit",
        "block_type": block_type,
        "skill": node.title,
        "hint_level": hint_level,
    }


async def park_tangent(
    db: AsyncSession, session: Session, text: str, *, node_id: str | None, events: EventWriter
) -> ParkingLotItem:
    item = ParkingLotItem(
        learner_id=session.learner_id, session_id=session.id, text=text, node_id=node_id
    )
    db.add(item)
    await db.commit()
    await events.emit(Verb.PARKED, ObjectType.NOTE, item.id, context={"node_id": node_id})
    return item
