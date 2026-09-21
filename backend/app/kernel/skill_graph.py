"""Skill graph: nodes, prerequisite edges, unlock gating and the Stage-1 "next skill" rule.

Deterministic; reads competency_state via kernel.competency. No LLM, no HTTP.
"""

from collections import deque
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningObject, SkillEdge, SkillNode
from app.kernel import competency, preferences

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


def teachable(node: SkillNode) -> bool:
    """Curriculum eligibility (P1): a node can be *taught* unless it is marked
    `assessment_requirements_json.teachable = false` — vocabulary decks are (they only ever run in
    the language block on FSRS). A genuine language lesson node stays eligible."""
    reqs = node.assessment_requirements_json or {}
    return bool(reqs.get("teachable", True))


async def _pick(db: AsyncSession, learner_id: str, order: list[SkillNode]) -> SkillNode | None:
    """First unlocked node below MASTERY_DONE in the given order; else the unlocked node with the
    lowest mastery; None when nothing in `order` is unlocked."""
    unlocked: list[tuple[float, SkillNode]] = []
    for node in order:
        if not await is_unlocked(db, learner_id, node.id):
            continue
        m = await competency.mastery(db, learner_id, node.id)
        if m < MASTERY_DONE:
            return node
        unlocked.append((m, node))
    return min(unlocked, key=lambda t: t[0])[1] if unlocked else None


async def next_skill(
    db: AsyncSession, learner_id: str, domain: str | None = None
) -> SkillNode | None:
    """Stage-1 planner rule: the first unlocked *teachable* node (topological order) below
    MASTERY_DONE; if everything unlocked is done, the unlocked node with the lowest mastery.
    A `goal.course` preference narrows the order to that course; when every goal node is still
    locked, the unlocked prerequisites *of* the goal come next, then the whole map. A locked node
    is never returned while an unlocked one exists."""
    order = [n for n in await topological_order(db, domain) if teachable(n)]
    goal = str(await preferences.get(db, learner_id, "goal.course") or "").strip()
    if goal:
        in_goal = [n for n in order if n.course == goal]
        if in_goal:  # a chosen goal narrows the map; an empty/unknown goal falls back to the map
            pick = await _pick(db, learner_id, in_goal)
            if pick is not None:
                return pick
            needed: set[str] = set()
            frontier = [n.id for n in in_goal]
            while frontier:
                for pre in await prerequisites(db, frontier.pop()):
                    if pre.id not in needed:
                        needed.add(pre.id)
                        frontier.append(pre.id)
            pick = await _pick(db, learner_id, [n for n in order if n.id in needed])
            if pick is not None:
                return pick
    pick = await _pick(db, learner_id, order)
    if pick is not None:
        return pick
    return order[0] if order else None


async def map_view(db: AsyncSession, learner_id: str) -> dict[str, Any]:
    """Open learner model: every node with mastery, dimensions, memory overlay and unlock state,
    every prerequisite edge, plus a Mermaid rendering (whole map first)."""
    order = await topological_order(db)
    nxt = await next_skill(db, learner_id)
    nodes = []
    for n in order:
        st = await competency.skill_state(db, learner_id, n.id)
        nodes.append(
            {
                "id": n.id,
                "slug": n.slug,
                "title": n.title,
                "domain": n.domain,
                "mastery": st["mastery"],
                "dimensions": st["dimensions"],
                "memory": st["memory"],
                "unlocked": await is_unlocked(db, learner_id, n.id),
                "is_next": bool(nxt and nxt.id == n.id),
            }
        )
    edges = [
        {"from": e.from_skill_id, "to": e.to_skill_id, "kind": e.kind} for e in await all_edges(db)
    ]
    return {"nodes": nodes, "edges": edges, "mermaid": to_mermaid(nodes, edges)}


def to_mermaid(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    def cls(n: dict[str, Any]) -> str:
        if n["mastery"] >= 0.6:
            return "done"
        if n["is_next"]:
            return "next"
        return "open" if n["unlocked"] else "locked"

    lines = ["graph LR"]
    ids = {n["id"]: f"n{i}" for i, n in enumerate(nodes)}
    for n in nodes:
        due = n["memory"].get("due", 0)
        label = f"{n['title']}<br/>{round(n['mastery'] * 100)}%" + (f" · {due} due" if due else "")
        lines.append(f'  {ids[n["id"]]}["{label}"]:::{cls(n)}')
    for e in edges:
        if e["from"] in ids and e["to"] in ids:
            lines.append(f"  {ids[e['from']]} --> {ids[e['to']]}")
    lines += [
        "  classDef done fill:#d9f2e3,stroke:#1f7a4d,color:#1f2328",
        "  classDef next fill:#dfe7fb,stroke:#2f5fd4,stroke-width:3px,color:#1f2328",
        "  classDef open fill:#ffffff,stroke:#5b6470,color:#1f2328",
        "  classDef locked fill:#f0f1f3,stroke:#d9dde3,color:#5b6470",
    ]
    return "\n".join(lines)
