"""Owner-selected curriculum scope, independent of optional project model integrations."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import DB, Learner
from app.kernel.learning_scope import FOCUS_TOPICS, reference_before

router = APIRouter(prefix="/learning-focus", tags=["learning-focus"])


class LearningFocusOut(BaseModel):
    reference_before: str | None
    topics: list[str]
    sound_learning: bool = False
    guitar_learning: bool = False
    old_corpus_role: str = "accuracy_review"


@router.get("", response_model=LearningFocusOut)
async def focus(db: DB, learner: Learner) -> LearningFocusOut:
    return LearningFocusOut(
        reference_before=await reference_before(db, learner.id), topics=FOCUS_TOPICS
    )
