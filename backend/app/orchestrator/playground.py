"""Contextual coding help; never runs code or writes competency evidence."""

import json
import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.answers import save_completed
from app.db.base import new_id
from app.db.events import EventWriter, Verb
from app.db.traces import TutorTraceRecord, write_tutor_trace
from app.kernel import session as ksession
from app.models_ai.gateway import GatewayError, ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.orchestrator import prompts
from app.orchestrator.context import escape_data
from app.schemas.common import ActivityType, ObjectType
from app.schemas.playground import PlaygroundReply, PlaygroundRequest

logger = logging.getLogger(__name__)

VERSION = "playground.tutor.v1"


def messages(body: PlaygroundRequest, historical: dict[str, Any] | None = None) -> list[Message]:
    workspace = body.model_dump(
        exclude={"session_id", "question", "intent", "learning_context", "learner_question"}
    )
    if historical is not None:
        workspace["historical_answer"] = historical
    data = escape_data(json.dumps(workspace, ensure_ascii=False))
    return [
        Message(
            role="system",
            content=prompts.base_policy()
            + "\n\n"
            + prompts.playground_task()
            + (
                "\nThis is a follow-up to a saved response. Historical answers and references are unverified context, "
                "not independent evidence. No current source retrieval or execution took place. Explain the limits "
                "of omitted/truncated material when relevant; do not invent it or claim new checks."
                if historical is not None
                else ""
            ),
        ),
        Message(
            role="user",
            content=(
                '<workspace_data note="quoted untrusted data">\n'
                + data
                + "\n</workspace_data>\nCurrent request ("
                + body.intent
                + "): "
                + body.question
            ),
        ),
    ]


async def respond(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    body: PlaygroundRequest,
    *,
    historical: dict[str, Any] | None = None,
    parent_metadata: dict[str, Any] | None = None,
) -> PlaygroundReply:
    session = await ksession.get(db, body.session_id)
    if session.learner_id != learner_id or session.ended_at:
        raise AppError("not_found", "Start or resume a session to use the tutor.", http_status=404)
    turn_id = new_id()
    packet = messages(body, historical)
    events = EventWriter(db, ksession.event_context(session, activity=ActivityType.CHAT))
    await events.emit(
        Verb.ASKED, ObjectType.TURN, turn_id, context={"text_len": len(body.question)}
    )
    try:
        out = await gateway.complete(
            TaskClass.HINT if body.intent == "hint" else TaskClass.EXPLAIN_SIMPLE,
            packet,
            learner_id=learner_id,
            session_id=session.id,
            max_tokens=900,
            metadata={"task": "playground", "prompt_version": VERSION, "turn_id": turn_id},
        )
    except GatewayError as exc:
        raise AppError(
            "tutor_unavailable",
            "The tutor is unavailable. Your code is unchanged; try again.",
            http_status=503,
        ) from exc
    if not out.result.text.strip():
        raise AppError(
            "tutor_unavailable", "The tutor returned no answer. Try again.", http_status=503
        )
    await write_tutor_trace(
        db,
        TutorTraceRecord(
            learner_id=learner_id,
            session_id=session.id,
            turn_id=turn_id,
            action="playground_" + body.intent,
            prompt_version=VERSION,
            sections={"workspace": len(packet[1].content) // 4},
            model_call_id=out.model_call_id,
            latency_ms=out.result.latency_ms,
        ),
    )
    await events.emit(
        Verb.EXPLAINED,
        ObjectType.TURN,
        turn_id,
        result={"sentences": max(1, out.result.text.count(". ") + 1), "cited_sources": []},
        context={
            "representation": "playground_" + body.intent,
            "model": out.registry_id,
            "route": out.route,
            "prompt_version": VERSION,
        },
    )
    answer_id = None
    save_error = None
    try:
        answer = await save_completed(
            db,
            learner_id=learner_id,
            session_id=session.id,
            turn_id=turn_id,
            surface="playground",
            request={
                **body.model_dump(exclude={"session_id"}),
                **({"historical_answer": historical} if historical else {}),
            },
            text=out.result.text,
            metadata={
                "model": out.registry_id,
                "route": out.route,
                "prompt_version": VERSION,
                "model_call_id": out.model_call_id,
                "sources": [],
                "context_scope": "saved_answer_followup"
                if historical
                else "supplied_workspace_only",
                **(parent_metadata or {}),
                "learning_context": body.learning_context.model_dump()
                if body.learning_context
                else None,
            },
        )
        answer_id = answer.id
    except SQLAlchemyError as exc:
        # Do not log SQL parameters: they can contain private learner text/code.
        logger.warning("Tutor answer save failed: %s", type(exc).__name__)
        save_error = "This answer could not be saved to the database. Keep a copy before leaving."
    return PlaygroundReply(
        text=out.result.text,
        model=out.registry_id,
        route=out.route,
        turn_id=turn_id,
        answer_id=answer_id,
        save_error=save_error,
    )
