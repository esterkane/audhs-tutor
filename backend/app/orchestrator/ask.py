"""Independent local tutoring, with explicit owned ancestry and atomic saved replies."""

from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import answers, ask_requests
from app.db.models import KnowledgeArea, TutorAnswer
from app.db.traces import TutorTraceRecord, write_tutor_trace
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.orchestrator.context import escape_data
from app.orchestrator.prompts import _read
from app.schemas.ask import AskQuestion, AskReply

PROMPT_VERSION = "ask.explain.v1"
MAX_HISTORY = 3


async def owned_answer(db: AsyncSession, learner_id: str, identity: str) -> TutorAnswer:
    answer = await db.scalar(
        select(TutorAnswer).where(
            TutorAnswer.id == identity,
            TutorAnswer.learner_id == learner_id,
            TutorAnswer.surface == "ask",
        )
    )
    if answer is None:
        raise AppError("not_found", "This Ask answer is unavailable.", 404)
    return answer


async def respond(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    body: AskQuestion,
    key: str,
    on_token: Callable[[str], Awaitable[None]] | None = None,
) -> AskReply:
    replay = await ask_requests.replay(db, learner_id, key, body.model_dump(mode="json"))
    if replay is not None:
        return AskReply.model_validate(replay[1])
    previous: list[TutorAnswer] = []
    cursor = body.parent_answer_id
    while cursor and len(previous) < MAX_HISTORY:
        row = await owned_answer(db, learner_id, cursor)
        previous.append(row)
        cursor = row.metadata_json.get("parent_answer_id")
    area_id = body.area_id
    if previous and previous[0].metadata_json.get("area_id") != area_id:
        raise AppError("topic_conflict", "Start a new question to change the area.", 409)
    area = await db.get(KnowledgeArea, area_id) if area_id else None
    if area_id and area is None:
        raise AppError("not_found", "This knowledge area is unavailable. Choose another area.", 404)
    # Capture all prompt inputs before the claim commits/expires read transactions.
    packet = [Message(role="system", content=_read("ask/explain.v1.md"))]
    if area:
        packet.append(
            Message(
                role="user", content=f"<area_context>\n{escape_data(area.title)}\n</area_context>"
            )
        )
    for row in reversed(previous):
        packet.extend(
            [
                Message(role="user", content=str(row.request_json["question"])),
                Message(role="assistant", content=row.text),
            ]
        )
    packet.append(Message(role="user", content=body.question))
    conversation_id = (
        str(previous[0].metadata_json.get("conversation_id") or previous[0].id)
        if previous
        else None
    )
    identity, completed = await ask_requests.claim(
        db, learner_id, key, body.model_dump(mode="json")
    )
    if completed is not None:
        return AskReply.model_validate(completed)
    metadata = {"surface": "ask", "prompt_version": PROMPT_VERSION, "turn_id": identity}
    if on_token:
        result = await gateway.complete_streamed(
            TaskClass.CHAT,
            packet,
            on_token=on_token,
            learner_id=learner_id,
            session_id=None,
            max_tokens=1600,
            metadata=metadata,
        )
    else:
        result = await gateway.complete(
            TaskClass.CHAT,
            packet,
            learner_id=learner_id,
            session_id=None,
            max_tokens=1600,
            metadata=metadata,
        )
    try:
        await write_tutor_trace(
            db,
            TutorTraceRecord(
                learner_id=learner_id,
                session_id=None,
                turn_id=identity,
                action="ask_explain",
                prompt_version=PROMPT_VERSION,
                model_call_id=result.model_call_id,
                latency_ms=result.result.latency_ms,
                dropped=["older_ancestry"] if cursor else [],
            ),
            commit=False,
        )
        answer = await answers.save_completed(
            db,
            learner_id=learner_id,
            session_id=None,
            turn_id=identity,
            surface="ask",
            request=body.model_dump(mode="json"),
            text=result.result.text,
            metadata={
                "area_id": area_id,
                "parent_answer_id": body.parent_answer_id,
                "conversation_id": conversation_id or identity,
                "prompt_version": PROMPT_VERSION,
                "model": result.registry_id,
                "route": result.route,
                "source_status": "not_requested",
                "check_status": "unverified",
                "origin_status": "unknown",
                "history_turns": len(previous),
            },
            commit=False,
        )
        reply = AskReply(
            text=answer.text,
            model=result.registry_id,
            route=result.route,
            turn_id=identity,
            answer_id=answer.id,
            saved_at=answer.created_at,
            conversation_id=conversation_id or identity,
            area_id=area_id,
            parent_answer_id=body.parent_answer_id,
            history_turns=len(previous),
            source_status="not_requested",
            source_note="Model explanation, not fact-checked. No sources retrieved for this answer.",
        )
        await ask_requests.complete(db, learner_id, identity, reply.model_dump(mode="json"))
        await db.commit()
        return reply
    except BaseException:
        await db.rollback()
        raise
