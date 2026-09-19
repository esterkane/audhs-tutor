from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import Learner

router = APIRouter(prefix="/learner", tags=["learner"])


class LearnerOut(BaseModel):
    id: str
    display_name: str
    created_at: str


@router.get(
    "/me", summary="The owner profile (single learner in Phase 1)", response_model=LearnerOut
)
async def me(learner: Learner) -> LearnerOut:
    return LearnerOut(
        id=learner.id, display_name=learner.display_name, created_at=learner.created_at
    )
