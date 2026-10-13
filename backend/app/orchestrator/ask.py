"""Independent local tutoring, with explicit owned ancestry and atomic saved replies."""

from collections.abc import Awaitable, Callable

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import answers, ask_requests
from app.db.models import KnowledgeArea, TutorAnswer
from app.db.traces import (
    RetrievalTraceRecord,
    TutorTraceRecord,
    write_retrieval_trace,
    write_tutor_trace,
)
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.orchestrator import ask_reuse, ask_sources
from app.orchestrator.answer_check_binding import text_hash
from app.orchestrator.context import escape_data
from app.orchestrator.prompts import _read, base_policy
from app.schemas.ask import AskQuestion, AskReply
from app.schemas.playground import PlaygroundSource

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
    *,
    quarantine_below_trust: int = 2,
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
    area_title = area.title if area else None
    sources = await ask_sources.resolve(db, body.sources, quarantine_below_trust)
    prompt_version = (
        "pedagogy.v2+ask.grounded.v1+sources.v2+contract.v3" if sources else PROMPT_VERSION
    )
    # Capture all prompt inputs before the claim commits/expires read transactions.
    packet = [
        Message(
            role="system",
            content=(base_policy() + "\n\n" + _read("ask/grounded.v1.md"))
            if sources
            else _read("ask/explain.v1.md"),
        )
    ]
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
    if sources:
        packet.append(Message(role="user", content=ask_sources.prompt_block(sources)))
    packet.append(
        Message(
            role="user",
            content=(
                f"<question>\n{escape_data(body.question)}\n</question>\n\n"
                + _read("ask/grounded-contract.v3.md")
                if sources
                else body.question
            ),
        )
    )
    conversation_id = (
        str(previous[0].metadata_json.get("conversation_id") or previous[0].id)
        if previous
        else None
    )
    context_snapshots = [
        {
            "answer_id": row.id,
            "answer_hash": text_hash(row.text),
            "question": row.request_json.get("question"),
            "text": row.text,
            "sources": row.metadata_json.get("sources", []),
            "source_text_hashes": row.metadata_json.get("source_text_hashes", {}),
            "origin_status": row.metadata_json.get("origin_status", "unknown"),
        }
        for row in previous
    ]
    reuse_binding, reuse_model_id = await ask_reuse.input_binding(
        db, gateway, learner_id, packet, sources, body
    )
    identity, completed = await ask_requests.claim(
        db, learner_id, key, body.model_dump(mode="json")
    )
    if completed is not None:
        return AskReply.model_validate(completed)
    if body.prefer_saved and not body.parent_answer_id:
        # Eligibility and receipt share one short writer transaction. Never hold
        # this lock while generating or contacting a model.
        await db.execute(text("BEGIN IMMEDIATE"))
        try:
            current_sources = await ask_sources.resolve(db, body.sources, quarantine_below_trust)
            current_title = (
                await db.scalar(select(KnowledgeArea.title).where(KnowledgeArea.id == area_id))
                if area_id
                else None
            )
            current_binding, _ = await ask_reuse.input_binding(
                db, gateway, learner_id, packet, current_sources, body
            )
            cached = (
                await ask_reuse.exact_saved(db, learner_id, body, current_binding)
                if (current_binding == reuse_binding and current_title == area_title)
                else None
            )
            if cached is not None:
                trace = await write_retrieval_trace(
                    db,
                    RetrievalTraceRecord(
                        learner_id=learner_id,
                        session_id=None,
                        collection="saved-ask-answer",
                        query=body.question,
                        filters={"answer_id": cached.id, "input_binding": reuse_binding},
                    ),
                    commit=False,
                )
                await write_tutor_trace(
                    db,
                    TutorTraceRecord(
                        learner_id=learner_id,
                        session_id=None,
                        turn_id=identity,
                        action="ask_reuse",
                        prompt_version=prompt_version,
                        retrieval_trace_id=trace.id,
                    ),
                    commit=False,
                )
                reply = AskReply(
                    text=cached.text,
                    model=str(cached.metadata_json.get("model", "saved")),
                    route="saved",
                    turn_id=identity,
                    answer_id=cached.id,
                    saved_at=cached.created_at,
                    conversation_id=str(cached.metadata_json.get("conversation_id") or cached.id),
                    area_id=area_id,
                    reused=True,
                    source_status="supplied" if sources else "not_requested",
                    sources=[
                        PlaygroundSource(
                            chunk_id=s["chunk_id"], citation=s["citation"], text=s["text"]
                        )
                        for s in sources
                    ],
                    source_note=(
                        "Reopened your Helpful saved answer for identical inputs. "
                        "Not fact-checked or refreshed from the web."
                    ),
                )
                await ask_requests.complete(db, learner_id, identity, reply.model_dump(mode="json"))
                await db.commit()
                return reply
            await db.commit()
        except BaseException:
            await db.rollback()
            raise
    metadata = {"surface": "ask", "prompt_version": prompt_version, "turn_id": identity}
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
    ask_sources.validate_citation_ids(result.result.text, sources)
    try:
        source_trace = (
            await write_retrieval_trace(
                db,
                RetrievalTraceRecord(
                    learner_id=learner_id,
                    session_id=None,
                    collection="explicit-local-passages",
                    query=body.question,
                    filters={
                        "mode": "explicit_selection",
                        "text_hashes": {s["chunk_id"]: s["text_hash"] for s in sources},
                    },
                    chunk_ids=[s["chunk_id"] for s in sources],
                    flagged_patterns=sorted({flag for s in sources for flag in s["flags"]}),
                ),
                commit=False,
            )
            if sources
            else None
        )
        await write_tutor_trace(
            db,
            TutorTraceRecord(
                learner_id=learner_id,
                session_id=None,
                turn_id=identity,
                action="ask_explain",
                prompt_version=prompt_version,
                model_call_id=result.model_call_id,
                latency_ms=result.result.latency_ms,
                retrieval_trace_id=source_trace.id if source_trace else None,
                sections={"selected_source_characters": sum(len(s["text"]) for s in sources)},
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
                "prompt_version": prompt_version,
                "model": result.registry_id,
                "route": result.route,
                "source_status": "supplied" if sources else "not_requested",
                "sources": sources,
                "source_text_hashes": {s["chunk_id"]: s["text_hash"] for s in sources},
                "context_snapshots": context_snapshots,
                "context_answer_ids": [s["answer_id"] for s in context_snapshots],
                "context_answer_hashes": {
                    s["answer_id"]: s["answer_hash"] for s in context_snapshots
                },
                "reuse_input_binding": reuse_binding
                if result.registry_id == reuse_model_id
                else None,
                "reuse_answer_hash": ask_reuse.digest(result.result.text),
                "check_status": "unverified",
                "origin_status": "source_derived" if sources or previous else "unknown",
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
            source_status="supplied" if sources else "not_requested",
            sources=[
                PlaygroundSource(chunk_id=s["chunk_id"], citation=s["citation"], text=s["text"])
                for s in sources
            ],
            source_note=(
                "Selected local passages supplied; citations are model suggestions, not fact-checked."
                if sources
                else "Model explanation, not fact-checked. No sources retrieved for this answer."
            ),
        )
        await ask_requests.complete(db, learner_id, identity, reply.model_dump(mode="json"))
        await db.commit()
        return reply
    except BaseException:
        await db.rollback()
        raise
