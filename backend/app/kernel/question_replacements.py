"""Resolve future practice only. Never use for submitted work or historical receipts."""

from sqlalchemy import select
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
        for key in ("exercise_id", "listening"):
            # These associations are immutable metadata, not editable question wording.
            # Validated status is a separate listening operation; preserve clip identity only.
            before, after = original.item_json.get(key), target.item_json.get(key)
            if key == "listening" and isinstance(before, dict) and isinstance(after, dict):
                identity = ("document_id", "chunk_id", "t_start", "t_end")
                before = {field: before.get(field) for field in identity}
                after = {field: after.get(field) for field in identity}
            if before != after:
                raise invalid()
        current = target
    raise invalid()


async def selected(db: AsyncSession, learner_id: str, candidate: Assessment) -> Assessment:
    """Validate an already ranked active candidate without redirecting its identity.

    Follow incoming links to the root, then verify the whole forward chain. This
    preserves the selector's skill/kind/attempt ordering and prevents a detached
    terminal from bypassing compatibility or predecessor-state checks.
    """
    root_id = candidate.id
    seen: set[str] = set()
    for _ in range(MAX_CHAIN):
        if root_id in seen:
            raise invalid()
        seen.add(root_id)
        parent = await db.scalar(
            select(QuestionReplacement.original_id).where(
                QuestionReplacement.learner_id == learner_id,
                QuestionReplacement.replacement_id == root_id,
            )
        )
        if parent is None:
            terminal = await resolve(db, learner_id, root_id)
            if terminal.id != candidate.id:
                raise invalid()
            return terminal
        root_id = parent
    raise invalid()
