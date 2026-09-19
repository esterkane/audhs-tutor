"""Skill graph: nodes, prerequisite edges, unlock gating and the Stage-1 "next skill" rule.

Deterministic; reads competency_state via kernel.competency. No LLM, no HTTP.
"""

from collections import deque
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningObject, SkillEdge, SkillNode
from app.kernel import competency

MASTERY_UNLOCK = 0.6  # prerequisites must reach this before a node is offered as new material
MASTERY_DONE = 0.6  # a node at/above this is not "the next thing to learn" any more


async def get_node(db: AsyncSession, skill_id: str) -> SkillNode:
    row = await db.get(SkillNode, skill_id)
    if row is None:
        raise KeyError(f"skill {skill_id!r} not found")
    return row


async def get_node_by_slug(db: AsyncSession, slug: str) -> SkillNode | None:
    return (await db.execute(select(SkillNode).where(SkillNode.slug == slug))).scalar_one_or_none()


async def all_nodes(db: AsyncSession, domain: str | None = None) -> Sequence[SkillNode]:
    stmt = select(SkillNode).order_by(SkillNode.created_at, SkillNode.id)  # ULIDs ≈ insertion order
    if domain:
        stmt = stmt.where(SkillNode.domain == domain)
    return (await db.execute(stmt)).scalars().all()


async def all_edges(db: AsyncSession) -> Sequence[SkillEdge]:
    return (await db.execute(select(SkillEdge))).scalars().all()


async def prerequisites(db: AsyncSession, skill_id: str) -> list[SkillNode]:
    stmt = (
        select(SkillNode)
        .join(SkillEdge, SkillEdge.from_skill_id == SkillNode.id)
        .where(SkillEdge.to_skill_id == skill_id, SkillEdge.kind == "prerequisite")
    )
    return list((await db.execute(stmt)).scalars().all())


async def topological_order(db: AsyncSession, domain: str | None = None) -> list[SkillNode]:
    """Kahn's algorithm over prerequisite edges; ties keep insertion order (stable seeds)."""
    nodes = list(await all_nodes(db, domain))
    ids = {n.id for n in nodes}
    indeg = {n.id: 0 for n in nodes}
    out: dict[str, list[str]] = {n.id: [] for n in nodes}
    for e in await all_edges(db):
        if e.kind == "prerequisite" and e.from_skill_id in ids and e.to_skill_id in ids:
            indeg[e.to_skill_id] += 1
            out[e.from_skill_id].append(e.to_skill_id)
    by_id = {n.id: n for n in nodes}
    queue = deque(n.id for n in nodes if indeg[n.id] == 0)
    order: list[SkillNode] = []
    while queue:
        cur = queue.popleft()
        order.append(by_id[cur])
        for nxt in out[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(nodes):
        raise ValueError("skill graph has a cycle")
    return order


async def learning_object_for(db: AsyncSession, skill_id: str) -> LearningObject | None:
    stmt = (
        select(LearningObject)
        .where(LearningObject.skill_id == skill_id)
        .order_by(LearningObject.version.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def is_unlocked(db: AsyncSession, learner_id: str, skill_id: str) -> bool:
    for pre in await prerequisites(db, skill_id):
        if await competency.mastery(db, learner_id, pre.id) < MASTERY_UNLOCK:
            return False
    return True


async def next_skill(
    db: AsyncSession, learner_id: str, domain: str | None = None
) -> SkillNode | None:
    """Stage-1 planner rule: the first unlocked node (topological order) below MASTERY_DONE;
    if everything unlocked is done, the unlocked node with the lowest mastery (keep deepening)."""
    order = await topological_order(db, domain)
    unlocked: list[tuple[float, SkillNode]] = []
    for node in order:
        if not await is_unlocked(db, learner_id, node.id):
            continue
        m = await competency.mastery(db, learner_id, node.id)
        if m < MASTERY_DONE:
            return node
        unlocked.append((m, node))
    if not unlocked:
        return order[0] if order else None
    return min(unlocked, key=lambda t: t[0])[1]
