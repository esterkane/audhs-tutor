"""Bounded local question matching and explicit feedback; never factual certification."""

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import answer_sources
from app.db.answer_eligibility import excluded_answer_ids
from app.db.answer_search import literal_query
from app.db.models import TutorAnswer, TutorAnswerFeedback
from app.schemas.answers import SavedSourceCheck


def context_dependent(row: TutorAnswer) -> bool:
    return bool(
        row.metadata_json.get("parent_answer_id")
        or row.metadata_json.get("context_answer_ids")
        or row.metadata_json.get("answer_memory")
        or row.request_json.get("historical_answer")
    )


async def ranked(
    db: AsyncSession, learner_id: str, query: str, area_id: str | None, limit: int
) -> list[tuple[TutorAnswer, SavedSourceCheck, str]]:
    question = func.coalesce(
        TutorAnswer.request_json["learner_question"].as_string(),
        TutorAnswer.request_json["question"].as_string(),
        TutorAnswer.request_json["text"].as_string(),
        "",
    )
    exact = func.trim(question) == query.strip()
    stmt = select(TutorAnswer).where(
        TutorAnswer.learner_id == learner_id,
        TutorAnswer.id.not_in(excluded_answer_ids(learner_id)),
        or_(
            TutorAnswer.surface == "ask",
            TutorAnswer.request_json["learner_question"].as_string().is_not(None),
        ),
    )
    if area_id:
        stmt = stmt.where(TutorAnswer.metadata_json["area_id"].as_string() == area_id)
    if query.strip():
        expression = literal_query(query)
        if not expression:
            stmt = stmt.where(exact)
        else:
            matches = (
                select(text("id"))
                .select_from(text("tutor_answer_fts"))
                .where(text("tutor_answer_fts MATCH :suggestion_query"))
            )
            stmt = stmt.where(or_(exact, TutorAnswer.id.in_(matches))).params(
                suggestion_query=f"request : ({expression}*)"
            )
        stmt = stmt.order_by(exact.desc())
    # Exact matches are included before recent partial matches. Quality ranking is
    # bounded to this pool, not a claim to have searched every historical review.
    rows = list((await db.scalars(stmt.order_by(TutorAnswer.id.desc()).limit(100))).all())
    checks = await answer_sources.check_many(db, learner_id, rows)
    reports = await db.execute(
        select(TutorAnswerFeedback.answer_id, TutorAnswerFeedback.verdict).where(
            TutorAnswerFeedback.learner_id == learner_id,
            TutorAnswerFeedback.answer_id.in_([row.id for row in rows]),
        )
    )
    feedback = {identity: verdict for identity, verdict in reports}

    def key(row: TutorAnswer) -> tuple[bool, bool, int]:
        label = (
            row.request_json.get("learner_question")
            or row.request_json.get("question")
            or row.request_json.get("text")
            or ""
        )
        same = bool(query.strip()) and str(label).strip() == query.strip()
        check = checks[row.id]
        risk = bool(
            check.omitted
            or context_dependent(row)
            or any(source.status != "unchanged" or source.newer_version for source in check.sources)
        )
        feedback_order = {"helpful": 0, "confusing": 2}.get(feedback.get(row.id) or "", 1)
        return not same, risk, feedback_order

    # Stable sorting preserves recency among otherwise equivalent candidates.
    rows.sort(key=key)
    result = []
    for row in rows[:limit]:
        same = not key(row)[0]
        reason = (
            "Same question text"
            if same
            else "Local question match"
            if query.strip()
            else "Saved question"
        )
        verdict = feedback.get(row.id)
        if verdict in {"helpful", "confusing"}:
            reason += f" · You marked it {verdict} (not a correctness check)"
        result.append((row, checks[row.id], reason))
    return result
