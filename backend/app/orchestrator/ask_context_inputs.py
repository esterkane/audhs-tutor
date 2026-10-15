"""Read-only owned inputs for a future context proposal; never generates or persists."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import TutorAnswer
from app.orchestrator import ask_sources
from app.orchestrator.answer_check_binding import text_hash
from app.orchestrator.ask_context_binding import ContextInput
from app.schemas.ask import AskSources, ConversationBrief


@dataclass(frozen=True)
class ProposalInputs:
    parent_answer_id: str
    area_id: str | None
    brief_json: str
    brief_hash: str
    inputs: dict[str, ContextInput]
    history_turns: int
    older_history_omitted: bool


async def resolve(
    db: AsyncSession,
    learner_id: str,
    parent_answer_id: str,
    area_id: str | None,
    brief: ConversationBrief,
    sources: AskSources | None = None,
    *,
    quarantine_below_trust: int = 2,
) -> ProposalInputs:
    """Only supplied parent ancestors and selected sources; no model/learning writes.

    The unsent brief is unverified context, not an attribution source. Accepted-note
    lineage must be resolved separately before eventual acceptance integration.
    """
    if (
        not isinstance(parent_answer_id, str)
        or not parent_answer_id.strip()
        or len(parent_answer_id) > 128
    ):
        raise AppError("context_invalid", "Choose a saved conversation first.", 422)
    if type(brief.version) is not int:
        raise AppError("context_invalid", "Retained notes have an invalid version.", 422)
    brief_json = ConversationBrief.model_validate(brief.model_dump()).model_dump_json()
    if sources is not None:
        sources = AskSources.model_validate(sources.model_dump())
    inputs: dict[str, ContextInput] = {}
    cursor: str | None = parent_answer_id
    seen: set[str] = set()
    count = 0
    while cursor and count < 3:
        if cursor in seen:
            raise AppError("context_invalid", "Conversation links could not be resolved.", 409)
        seen.add(cursor)
        row = await db.scalar(
            select(TutorAnswer)
            .where(
                TutorAnswer.id == cursor,
                TutorAnswer.learner_id == learner_id,
                TutorAnswer.surface == "ask",
            )
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise AppError("not_found", "This conversation is unavailable.", 404)
        if row.metadata_json.get("area_id") != area_id:
            raise AppError("topic_conflict", "Choose a conversation in the current area.", 409)
        question = row.request_json.get("question")
        if not isinstance(question, str) or not question.strip() or not row.text.strip():
            raise AppError("context_invalid", "A saved conversation turn is incomplete.", 409)
        inputs[f"T{count + 1}:question"] = ContextInput(
            question,
            "learner_statement",
            row.id,
            text_hash(question),
        )
        inputs[f"T{count + 1}:answer"] = ContextInput(
            row.text,
            "unverified_tutor_reply",
            row.id,
            text_hash(row.text),
        )
        raw_parent = row.metadata_json.get("parent_answer_id")
        if raw_parent is not None and (not isinstance(raw_parent, str) or not raw_parent.strip()):
            raise AppError("context_invalid", "Conversation links could not be resolved.", 409)
        cursor = raw_parent
        count += 1
    if cursor in seen:
        raise AppError("context_invalid", "Conversation links could not be resolved.", 409)
    for source in await ask_sources.resolve(db, sources, quarantine_below_trust):
        inputs[source["source_key"]] = ContextInput(
            source["text"],
            "selected_source",
            source["chunk_id"],
            text_hash(source["document_version_id"] + ":" + source["text_hash"]),
        )
    if len(brief_json) + sum(len(item.text) for item in inputs.values()) > 24000:
        raise AppError("context_too_large", "Choose fewer passages or shorten retained notes.", 422)
    return ProposalInputs(
        parent_answer_id, area_id, brief_json, text_hash(brief_json), inputs, count, bool(cursor)
    )
