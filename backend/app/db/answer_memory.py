"""Bounded historical hints, not an authoritative knowledge source."""

from typing import Any

from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.answer_eligibility import excluded_answer_ids
from app.db.answer_search import literal_query
from app.db.models import TutorAnswer
from app.schemas.playground import PlaygroundRequest


def candidates(learner_id: str, body: PlaygroundRequest) -> Select[tuple[TutorAnswer]] | None:
    context = body.learning_context
    if not context or not context.target_id:
        return None
    excluded = excluded_answer_ids(learner_id)
    stmt = select(TutorAnswer).where(
        TutorAnswer.learner_id == learner_id,
        TutorAnswer.surface == "playground",
        TutorAnswer.id.not_in(excluded),
        func.coalesce(func.json_array_length(TutorAnswer.metadata_json["answer_memory"]), 0) == 0,
        TutorAnswer.request_json["historical_answer"].as_string().is_(None),
    )
    for key in ("course_id", "section_id", "target_id"):
        value = getattr(context, key)
        field = TutorAnswer.metadata_json["learning_context"][key].as_string()
        stmt = stmt.where(field == value if value is not None else field.is_(None))
    # Compare supplied work exactly. No claim is made about files not supplied in this request.
    for key in (
        "exercise",
        "code",
        "output",
        "output_stale",
        "intent",
        "questioning_style",
        "learner_answer",
    ):
        field = TutorAnswer.request_json[key]
        stmt = stmt.where(
            (field.as_boolean() if key == "output_stale" else field.as_string())
            == getattr(body, key)
        )
    return stmt


async def retrieve(
    db: AsyncSession, learner_id: str, body: PlaygroundRequest
) -> list[dict[str, str]]:
    stmt = candidates(learner_id, body)
    expression = literal_query((body.learner_question or body.question).strip()[:200])
    if stmt is None or not expression:
        return []
    stmt = stmt.where(
        TutorAnswer.id.in_(
            select(text("id"))
            .select_from(text("tutor_answer_fts"))
            .where(text("tutor_answer_fts MATCH :memory_query"))
        )
    ).params(memory_query=expression)
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
    # Exact reuse is independent of relevance/FTS ranking: newer related conversations
    # must not displace an identical request, and punctuation-only questions still match.
    stmt = candidates(learner_id, body)
    if stmt is None:
        return None
    stmt = stmt.where(TutorAnswer.metadata_json["prompt_version"].as_string() == prompt_version)

    def fields(value: Any, path: str) -> list[ColumnElement[bool]]:
        field = func.json_extract(TutorAnswer.request_json, path)
        kind = func.json_type(TutorAnswer.request_json, path)
        if isinstance(value, dict):
            return [kind == "object"] + [
                clause for key, child in value.items() for clause in fields(child, path + "." + key)
            ]
        if isinstance(value, list):
            return [kind == "array", func.json_array_length(field) == len(value)] + [
                clause for i, child in enumerate(value) for clause in fields(child, f"{path}[{i}]")
            ]
        if value is None:
            return [kind == "null"]
        if isinstance(value, bool):
            return [kind == ("true" if value else "false")]
        return [kind == "text", field == value]

    for key, value in expected.items():
        stmt = stmt.where(*fields(value, "$." + key))
    rows = await db.scalars(stmt.order_by(TutorAnswer.id.desc()).limit(20))
    for row in rows:
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
