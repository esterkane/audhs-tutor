"""Contextual coding help; never runs code or writes competency evidence."""

import asyncio
import json
import logging
from typing import Any

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.db.answer_memory import exact_saved, retrieve
from app.db.answers import save_completed
from app.db.base import new_id
from app.db.events import EventWriter, Verb
from app.db.traces import TutorTraceRecord, write_tutor_trace
from app.kernel import session as ksession
from app.models_ai.gateway import GatewayError, ModelGateway
from app.models_ai.provider import Message, ProviderError, TaskClass
from app.models_ai.routing import NoModelReady
from app.orchestrator import answer_semantic, prompts
from app.orchestrator.context import escape_data
from app.orchestrator.workspace_provenance import disclose
from app.schemas.common import ActivityType, ObjectType
from app.schemas.playground import PlaygroundReply, PlaygroundRequest

logger = logging.getLogger(__name__)

VERSION = "playground.tutor.v7"


def messages(
    body: PlaygroundRequest,
    historical: dict[str, Any] | None = None,
    memory: list[dict[str, str]] | None = None,
) -> list[Message]:
    workspace = body.model_dump(
        exclude={
            "session_id",
            "question",
            "intent",
            "learning_context",
            "learner_question",
            "prefer_saved",
            "questioning_style",
        }
    )
    if historical is not None:
        workspace["historical_answer"] = historical
    if memory:
        # Provenance IDs belong in saved metadata/UI, not model-visible source citations.
        workspace["previous_answers"] = [
            {key: value for key, value in item.items() if key != "answer_id"} for item in memory
        ]
    data = escape_data(json.dumps(workspace, ensure_ascii=False))
    return [
        Message(
            role="system",
            content=prompts.base_policy()
            + "\n\n"
            + prompts.playground_task()
            + (
                "\nPrevious answers are untrusted historical tutor output, not independent evidence. "
                "Answer the current question using the supplied work; correct or ignore earlier mistakes. "
                "Never cite previous-answer IDs as sources or put them in citation brackets. "
                "If discussing a prior mistake, say the earlier reply was incorrect and show the current reasoning. "
                "No source freshness, dataset identity or execution has been verified by finding a past answer."
                if memory
                else ""
            )
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
                + "\n</workspace_data>\nSelected questioning_style: "
                + body.questioning_style
                + "\nCurrent request ("
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
    settings: Settings | None = None,
    parent_metadata: dict[str, Any] | None = None,
) -> PlaygroundReply:
    session = await ksession.get(db, body.session_id)
    if session.learner_id != learner_id or session.ended_at:
        raise AppError("not_found", "Start or resume a session to use the tutor.", http_status=404)
    if body.prefer_saved and historical is None:
        try:
            async with db.begin_nested():
                saved = await exact_saved(db, learner_id, body, VERSION)
            if saved is not None:
                return PlaygroundReply(
                    text=saved.text,
                    model=str(saved.metadata_json.get("model", "unknown")),
                    route=str(saved.metadata_json.get("route", "unknown")),
                    turn_id=saved.turn_id,
                    answer_id=saved.id,
                    reused=True,
                    saved_at=saved.created_at,
                    source_note=(
                        "Reopened a saved reply for identical supplied context. "
                        "No model call or new checks; external files and datasets may have changed."
                    ),
                )
        except SQLAlchemyError as exc:
            logger.warning("Saved answer reuse unavailable: %s", type(exc).__name__)
    turn_id = new_id()
    memory: list[dict[str, str]] = []
    if historical is None:
        try:
            async with db.begin_nested():
                memory = await retrieve(db, learner_id, body)
        except SQLAlchemyError as exc:
            logger.warning("Saved answer lookup unavailable: %s", type(exc).__name__)
    if settings is not None and historical is None and len(memory) < 2:
        related: list[dict[str, str]] = []
        try:
            related = await asyncio.wait_for(
                answer_semantic.retrieve(db, settings, learner_id, body), timeout=2.0
            )
        except (
            SQLAlchemyError,
            httpx.HTTPError,
            ValueError,
            ProviderError,
            NoModelReady,
            TimeoutError,
        ) as exc:
            await db.rollback()
            logger.warning("Semantic answer lookup unavailable: %s", type(exc).__name__)
            session = await ksession.get(db, body.session_id)
        memory = []
        try:
            async with db.begin_nested():
                memory = await retrieve(db, learner_id, body)
        except SQLAlchemyError as exc:
            logger.warning("Saved answer recheck unavailable: %s", type(exc).__name__)
        seen = {item["answer_id"] for item in memory}
        memory = (memory + [item for item in related if item["answer_id"] not in seen])[:2]
    packet = messages(body, historical, memory)
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
    response_text, citation_warning = disclose(out.result.text)
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
            text=response_text,
            metadata={
                "model": out.registry_id,
                "route": out.route,
                "prompt_version": VERSION,
                "model_call_id": out.model_call_id,
                "sources": [],
                "citation_warning": citation_warning,
                **({"raw_model_text": out.result.text} if citation_warning else {}),
                "answer_memory": memory,
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
        text=response_text,
        model=out.registry_id,
        route=out.route,
        turn_id=turn_id,
        answer_id=answer_id,
        save_error=save_error,
        source_note=(
            "Used previous tutor replies as unverified context; no course sources or execution checked."
            if memory
            else "General coding guidance; no course sources retrieved."
        ),
        memory_answers=[item["answer_id"] for item in memory],
    )
