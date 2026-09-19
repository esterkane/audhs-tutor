from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import DB, Gateway, Learner, Repo
from app.kernel import competency, skill_graph
from app.kernel import representations as krep
from app.kernel import session as ksession
from app.orchestrator import representations as orep

router = APIRouter(prefix="/objects", tags=["representations"])


class KindsOut(BaseModel):
    object_id: str
    concept: str
    kinds: list[dict[str, object]]  # {kind, label, cached, allowed}


class RenderIn(BaseModel):
    session_id: str
    force: bool = False


class RenderOut(BaseModel):
    object_id: str
    skill_id: str
    concept: str
    kind: str
    content: str
    representation_id: str
    model_call_id: str | None
    cached: bool
    sources: list[str]


class PreferIn(BaseModel):
    session_id: str
    chosen_id: str
    rejected_id: str
    reason: str | None = None


@router.get(
    "/{skill_id}/representations",
    summary="Representation kinds for a skill's LearningObject (cached/allowed flags)",
    response_model=KindsOut,
)
async def kinds(skill_id: str, db: DB, learner: Learner) -> KindsOut:
    obj = await krep.object_for_skill(db, skill_id)
    if obj is None:
        raise KeyError("no learning object for this skill")
    cached = await krep.cached_kinds(db, obj.id)
    allowed = krep.allowed_kinds(await competency.mastery(db, learner.id, skill_id))
    return KindsOut(
        object_id=obj.id,
        concept=obj.concept,
        kinds=[
            {
                "kind": k,
                "label": krep.KIND_LABELS[k],
                "cached": k in cached,
                "allowed": k in allowed,
            }
            for k in krep.KINDS
        ],
    )


@router.post(
    "/{skill_id}/representations/prefer",
    summary="Record which of two representations worked better (preferred event)",
    status_code=204,
)
async def prefer(skill_id: str, body: PreferIn, db: DB) -> None:
    s = await ksession.get(db, body.session_id)
    await orep.prefer(db, s, body.chosen_id, body.rejected_id, body.reason)


@router.post(
    "/{skill_id}/representations/{kind}",
    summary="Show it differently: render (or fetch cached) one representation",
    response_model=RenderOut,
)
async def render(
    skill_id: str, kind: str, body: RenderIn, db: DB, gateway: Gateway, repo: Repo
) -> RenderOut:
    s = await ksession.get(db, body.session_id)
    node = await skill_graph.get_node(db, skill_id)
    out = await orep.render(db, gateway, repo, s, node, kind, force=body.force)
    return RenderOut.model_validate(out)
