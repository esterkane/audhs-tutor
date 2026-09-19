from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import DB, Gateway, Learner, Repo
from app.kernel import session as ksession
from app.kernel import skill_graph
from app.orchestrator import challenge
from app.orchestrator.grader import Grader
from app.schemas.challenge import CHALLENGE_MODES, ChallengeStart, ChallengeView
from app.schemas.grading import AttemptRequest, AttemptResult

router = APIRouter(prefix="/challenge", tags=["challenge"])


class ModesOut(BaseModel):
    modes: list[dict[str, str]]


MODE_HINTS = {
    "planted_error": "Find the one planted error in a short explanation.",
    "steelman": "Argue the strongest case for a wrong claim, then break it.",
    "teach_back": "Explain it to a specific student persona.",
    "calibration": "Three quick questions, each with a confidence rating.",
}


@router.get(
    "/modes",
    summary="Available critical-thinking challenge modes (opt-in)",
    response_model=ModesOut,
)
async def modes() -> ModesOut:
    return ModesOut(modes=[{"mode": m, "hint": MODE_HINTS[m]} for m in CHALLENGE_MODES])


@router.post(
    "/start",
    summary="Generate (or reuse) a challenge item for the current skill",
    response_model=ChallengeView,
)
async def start(
    body: ChallengeStart, db: DB, gateway: Gateway, repo: Repo, learner: Learner
) -> ChallengeView:
    s = await ksession.get(db, body.session_id)
    skill_id = body.skill_id or (await ksession.load_checkpoint(db, s.id) or {}).get("skill_id")
    if not skill_id:
        nxt = await skill_graph.next_skill(db, learner.id)
        if nxt is None:
            raise KeyError("no skills")
        skill_id = nxt.id
    node = await skill_graph.get_node(db, skill_id)
    return await challenge.start(db, gateway, repo, s, node, body.mode)


@router.post(
    "/submit",
    summary="Submit a challenge answer (graded against the hidden key; schedules a delayed item)",
    response_model=AttemptResult,
)
async def submit(body: AttemptRequest, db: DB, gateway: Gateway) -> AttemptResult:
    return await Grader(db, gateway).grade(body)
