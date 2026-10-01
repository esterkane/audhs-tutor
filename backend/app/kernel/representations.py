"""Representation cache (ADR-0007): LearningObject is the source of truth; Representations are lazily
rendered views keyed by (object_id, kind). "Show it differently" never changes the object."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningObject, Representation

KINDS = ["analogy", "derivation", "code", "diagram", "worked_example", "problem_first", "narrative"]
KIND_LABELS = {
    "analogy": "Analogy", "derivation": "Derivation", "code": "Code", "diagram": "Diagram in words",
    "worked_example": "Worked example", "problem_first": "Problem first", "narrative": "Narrative",
}  # fmt: skip


def allowed_kinds(mastery: float) -> list[str]:
    """Problem-first only once the node is reasonably mastered (expertise reversal)."""
    return [k for k in KINDS if k != "problem_first" or mastery >= 0.6]


async def get_cached(db: AsyncSession, object_id: str, kind: str) -> Representation | None:
    stmt = (
        select(Representation)
        .where(Representation.object_id == object_id, Representation.kind == kind)
        .order_by(Representation.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def cached_kinds(db: AsyncSession, object_id: str) -> set[str]:
    stmt = select(Representation.kind).where(Representation.object_id == object_id)
    return set((await db.execute(stmt)).scalars().all())


async def store(
    db: AsyncSession, object_id: str, kind: str, content: str, *, model_call_id: str | None
) -> Representation:
    if kind not in KINDS:
        raise ValueError(f"unknown representation kind {kind!r}")
    row = Representation(
        object_id=object_id, kind=kind, content=content, model_call_id=model_call_id, cached=True
    )
    db.add(row)
    await db.commit()
    return row


async def invalidate(db: AsyncSession, object_id: str, kind: str | None = None) -> int:
    stmt = select(Representation).where(Representation.object_id == object_id)
    if kind:
        stmt = stmt.where(Representation.kind == kind)
    rows = list((await db.execute(stmt)).scalars())
    for r in rows:
        await db.delete(r)
    await db.commit()
    return len(rows)


async def object_for_skill(db: AsyncSession, skill_id: str) -> LearningObject | None:
    stmt = (
        select(LearningObject)
        .where(LearningObject.skill_id == skill_id)
        .order_by(LearningObject.version.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()
