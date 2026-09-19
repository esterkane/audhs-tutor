from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import DB, Gateway, Learner
from app.kernel import session as ksession
from app.orchestrator.grader import Grader, view
from app.schemas.grading import AssessmentView, AttemptRequest, AttemptResult

router = APIRouter(prefix="/assess", tags=["assess"])


class NextItem(BaseModel):
    item: AssessmentView | None
    skill_id: str


@router.get(
    "/next",
    summary="Next assessment item for a skill (mcq → cloze → explain-back rotation)",
    response_model=NextItem,
)
async def next_item(
    db: DB,
    gateway: Gateway,
    learner: Learner,
    session_id: str = Query(...),
    skill_id: str | None = None,
) -> NextItem:
    s = await ksession.get(db, session_id)
    if skill_id is None:
        cp = await ksession.load_checkpoint(db, s.id) or {}
        skill_id = cp.get("skill_id")
    if skill_id is None:
        from app.kernel import skill_graph

        nxt = await skill_graph.next_skill(db, learner.id)
        if nxt is None:
            raise KeyError("no skills")
        skill_id = nxt.id
    a = await Grader(db, gateway).next_item(learner.id, skill_id)
    return NextItem(item=view(a) if a else None, skill_id=skill_id)


@router.post(
    "/attempt",
    summary="Submit an answer with a prior confidence rating; graded hierarchically",
    response_model=AttemptResult,
)
async def attempt(body: AttemptRequest, db: DB, gateway: Gateway) -> AttemptResult:
    return await Grader(db, gateway).grade(body)
