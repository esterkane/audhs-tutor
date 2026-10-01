"""Scoped, source-current historical lesson answers; not learning evidence."""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.answer_search import literal_query
from app.db.answer_sources import check
from app.db.models import TutorAnswer, TutorAnswerFeedback


async def retrieve(
    db: AsyncSession,
    learner_id: str,
    skill_id: str,
    question: str,
    action: str,
    questioning_style: str,
    contract_key: str,
) -> list[dict[str, str]]:
    expression = literal_query(question[:200])
    if not expression:
        return []
    excluded = select(TutorAnswerFeedback.answer_id).where(
        TutorAnswerFeedback.learner_id == learner_id,
        TutorAnswerFeedback.hidden.is_(True)
        | TutorAnswerFeedback.verdict.in_(["incorrect", "outdated"]),
    )
    rows = await db.scalars(
        select(TutorAnswer)
        .where(
            TutorAnswer.learner_id == learner_id,
            TutorAnswer.surface == "tutor",
            TutorAnswer.metadata_json["teaching_contract_key"].as_string() == contract_key,
            TutorAnswer.metadata_json["skill_id"].as_string() == skill_id,
            TutorAnswer.metadata_json["teaching_action"].as_string() == action,
            TutorAnswer.metadata_json["questioning_style"].as_string() == questioning_style,
            func.coalesce(func.json_array_length(TutorAnswer.metadata_json["answer_memory"]), 0)
            == 0,
            TutorAnswer.id.not_in(excluded),
            TutorAnswer.id.in_(
                select(text("id"))
                .select_from(text("tutor_answer_fts"))
                .where(text("tutor_answer_fts MATCH :lesson_query"))
            ),
        )
        .params(lesson_query=expression)
        .order_by(TutorAnswer.id.desc())
        .limit(5)
    )
    result = []
    for row in rows:
        status = await check(db, learner_id, row.id)
        if (
            not status.sources
            or status.omitted
            or any(s.status != "unchanged" or s.newer_version for s in status.sources)
        ):
            continue
        result.append(
            {
                "answer_id": row.id,
                "saved_at": row.created_at,
                "question": str(row.request_json.get("text", ""))[:200],
                "excerpt": row.text[:600],
            }
        )
        if len(result) == 2:
            break
    return result
