"""Bounded historical hints, not an authoritative knowledge source."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.answer_search import literal_query
from app.db.models import TutorAnswer, TutorAnswerFeedback
from app.schemas.playground import PlaygroundRequest


async def retrieve(
    db: AsyncSession, learner_id: str, body: PlaygroundRequest
) -> list[dict[str, str]]:
    context = body.learning_context
    question = (body.learner_question or body.question).strip()
    expression = literal_query(question[:200])
    if not context or not context.target_id or not expression:
        return []
    excluded = select(TutorAnswerFeedback.answer_id).where(
        TutorAnswerFeedback.learner_id == learner_id,
        TutorAnswerFeedback.hidden.is_(True)
        | TutorAnswerFeedback.verdict.in_(["incorrect", "outdated"]),
    )
    stmt = (
        select(TutorAnswer)
        .where(
            TutorAnswer.learner_id == learner_id,
            TutorAnswer.surface == "playground",
            TutorAnswer.id.not_in(excluded),
            TutorAnswer.id.in_(
                select(text("id"))
                .select_from(text("tutor_answer_fts"))
                .where(text("tutor_answer_fts MATCH :memory_query"))
            ),
        )
        .params(memory_query=expression)
    )
    for key in ("course_id", "section_id", "target_id"):
        value = getattr(context, key)
        field = TutorAnswer.metadata_json["learning_context"][key].as_string()
        stmt = stmt.where(field == value if value is not None else field.is_(None))
    # Compare supplied work exactly. No claim is made about files not supplied in this request.
    for key in ("exercise", "code", "output", "output_stale", "intent"):
        field = TutorAnswer.request_json[key]
        stmt = stmt.where(
            (field.as_boolean() if key == "output_stale" else field.as_string())
            == getattr(body, key)
        )
    rows = await db.scalars(stmt.order_by(TutorAnswer.id.desc()).limit(20))
    result = []
    for row in rows:
        if row.metadata_json.get("answer_memory") or row.request_json.get("historical_answer"):
            continue
        result.append(
            {
                "answer_id": row.id,
                "saved_at": row.created_at,
                "question": str(
                    row.request_json.get("learner_question")
                    or row.request_json.get("question")
                    or ""
                )[:400],
                "excerpt": row.text[:1200],
            }
        )
        if len(result) == 2:
            break
    return result


async def exact_saved(
    db: AsyncSession, learner_id: str, body: PlaygroundRequest, prompt_version: str
) -> TutorAnswer | None:
    """Reopen identical supplied requests, never certify dataset or external-source freshness."""
    from app.db.answer_sources import check

    expected = body.model_dump(exclude={"session_id", "prefer_saved"})
    # Use the same ownership, negative-feedback and workspace filters as memory retrieval.
    for candidate in await retrieve(db, learner_id, body):
        row = await db.get(TutorAnswer, candidate["answer_id"])
        if row is None or row.metadata_json.get("prompt_version") != prompt_version:
            continue
        previous = {key: value for key, value in row.request_json.items() if key != "prefer_saved"}
        if previous != expected:
            continue
        sources = await check(db, learner_id, row.id)
        if sources.omitted or any(
            source.status != "unchanged" or source.newer_version for source in sources.sources
        ):
            continue
        return row
    return None
