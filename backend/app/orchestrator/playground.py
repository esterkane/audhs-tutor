"""Contextual coding help; never runs code or writes competency evidence."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
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

VERSION = "playground.tutor.v1"


def messages(body: PlaygroundRequest) -> list[Message]:
    workspace = body.model_dump(exclude={"session_id", "question", "intent"})
    data = escape_data(json.dumps(workspace, ensure_ascii=False))
    return [
        Message(role="system", content=prompts.base_policy() + "\n\n" + prompts.playground_task()),
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
    db: AsyncSession, gateway: ModelGateway, learner_id: str, body: PlaygroundRequest
) -> PlaygroundReply:
    session = await ksession.get(db, body.session_id)
    if session.learner_id != learner_id or session.ended_at:
        raise AppError("not_found", "Start or resume a session to use the tutor.", http_status=404)
    turn_id = new_id()
    packet = messages(body)
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
    return PlaygroundReply(
        text=out.result.text, model=out.registry_id, route=out.route, turn_id=turn_id
    )
