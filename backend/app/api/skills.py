from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import DB, Learner
from app.db.models import SkillNode
from app.kernel import competency, skill_graph
from app.schemas.tutor import SkillView

router = APIRouter(prefix="/skills", tags=["skills"])


async def _view(db: DB, learner_id: str, node: SkillNode) -> SkillView:
    state = await competency.skill_state(db, learner_id, node.id)
    return SkillView(
        id=node.id,
        slug=node.slug,
        title=node.title,
        description=node.description,
        domain=node.domain,
        success_criteria=list(node.success_criteria_json or []),
        prerequisites=[p.slug for p in await skill_graph.prerequisites(db, node.id)],
        mastery=state["mastery"],
        unlocked=await skill_graph.is_unlocked(db, learner_id, node.id),
        state=state,
    )


class SkillList(BaseModel):
    skills: list[SkillView]
    next_skill_id: str | None


@router.get(
    "",
    summary="Skill map with mastery + unlock state (open learner model)",
    response_model=SkillList,
)
async def list_skills(db: DB, learner: Learner) -> SkillList:
    nodes = await skill_graph.topological_order(db)
    nxt = await skill_graph.next_skill(db, learner.id)
    return SkillList(
        skills=[await _view(db, learner.id, n) for n in nodes],
        next_skill_id=nxt.id if nxt else None,
    )


class MapOut(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    mermaid: str


@router.get(
    "/map",
    summary="Whole skill map with competency + memory overlays and a Mermaid rendering",
    response_model=MapOut,
)
async def skill_map(db: DB, learner: Learner) -> MapOut:
    return MapOut.model_validate(await skill_graph.map_view(db, learner.id))


@router.get("/{skill_id}", summary="One skill with its state", response_model=SkillView)
async def get_skill(skill_id: str, db: DB, learner: Learner) -> SkillView:
    return await _view(db, learner.id, await skill_graph.get_node(db, skill_id))
