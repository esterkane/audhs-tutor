"""Resolve future practice only. Never use for submitted work or historical receipts."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import Assessment, QuestionReplacement
from app.kernel import question_state

MAX_CHAIN = 64


def invalid() -> AppError:
    return AppError(
        "question_replacement_invalid",
        "This replacement is unavailable. Your previous work is retained.",
        409,
    )


async def resolve(db: AsyncSession, learner_id: str, assessment_id: str) -> Assessment:
    """Read a bounded, compatible owned chain; reject broken lineage rather than fall back."""
    original = await question_state.require_visible(db, learner_id, assessment_id)
    current = original
    seen: set[str] = set()
    for _ in range(MAX_CHAIN):
        if current.id in seen:
            raise invalid()
        seen.add(current.id)
        link = await db.get(QuestionReplacement, (learner_id, current.id), populate_existing=True)
        if link is None:
            await question_state.require_active(db, learner_id, current.id)
            return current
        state = await question_state.read(db, learner_id, current.id)
        if state.state != "superseded":
            raise invalid()
        target = await question_state.require_visible(db, learner_id, link.replacement_id)
        if (
            target.owner_learner_id != learner_id
            or target.skill_id != original.skill_id
            or target.kind != original.kind
        ):
            raise invalid()
        current = target
    raise invalid()
