from fastapi import APIRouter

from app.api.deps import DB, Learner
from app.kernel import study_conditions
from app.schemas.study_conditions import ConditionsIn, ConditionsOut, ConditionsSummary

router = APIRouter(prefix="/study-conditions", tags=["experiments"])


@router.post("", response_model=ConditionsOut)
async def record(body: ConditionsIn, db: DB, learner: Learner) -> ConditionsOut:
    return await study_conditions.record(db, learner.id, body)


@router.get("/summary", response_model=ConditionsSummary)
async def summary(db: DB, learner: Learner) -> ConditionsSummary:
    return await study_conditions.summary(db, learner.id)
