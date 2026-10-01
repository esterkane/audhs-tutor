"""Paraphrase lookup with lesson scope and source currency rechecked after inference."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.answer_sources import check
from app.db.lesson_answer_memory import candidates
from app.orchestrator.answer_semantic import ranked


async def retrieve(
    db: AsyncSession,
    settings: Settings,
    learner_id: str,
    skill_id: str,
    question: str,
    action: str,
    questioning_style: str,
    contract_key: str,
) -> list[dict[str, str]]:
    if not question.strip():
        return []
    rows = await ranked(
        db,
        settings,
        learner_id,
        candidates(learner_id, skill_id, action, questioning_style, contract_key),
        question.strip()[:2000],
    )
    result = []
    for row in rows:
        status = await check(db, learner_id, row["answer_id"])
        if (
            not status.sources
            or status.omitted
            or any(
                source.status != "unchanged" or source.newer_version for source in status.sources
            )
        ):
            continue
        result.append({**row, "question": row["question"][:200], "excerpt": row["excerpt"][:600]})
    return result
