"""Contextual coding help; never runs code or writes competency evidence."""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any, Literal

import httpx
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.answer_recovery import AnswerRecovery
from app.core.config import Settings
from app.core.errors import AppError
from app.db.answer_memory import exact_saved, retrieve
from app.db.answers import save_completed
from app.db.base import new_id, utcnow_iso
from app.db.events import EventWriter, Verb
from app.db.models import Session, SessionCheckpoint, SkillNode
from app.db.traces import TutorTraceRecord, write_retrieval_trace, write_tutor_trace
from app.kernel import session as ksession
from app.kernel import skill_graph
from app.kernel.arithmetic_checks import VERSION as ARITHMETIC_VERSION
from app.kernel.bin_checks import VERSION as BIN_VERSION
from app.knowledge.repository import RetrievalRepository
from app.models_ai.gateway import GatewayError, ModelGateway, OutputLimitError
from app.models_ai.provider import Message, ProviderError, TaskClass
from app.models_ai.routing import NoModelReady
from app.orchestrator import answer_semantic, prompts, tools
from app.orchestrator.bin_feedback import respond_bins
from app.orchestrator.context import escape_data
from app.orchestrator.feedback_render import render_feedback
from app.orchestrator.lesson_evidence import LessonEvidence
from app.orchestrator.lesson_evidence import snapshot as evidence_snapshot
from app.orchestrator.workspace_checks import (
    bin_checks_for,
    bin_summary,
    checks_for,
    disclose_arithmetic,
    disclose_bins,
    summary,
)
from app.orchestrator.workspace_provenance import disclose
from app.schemas.common import ActivityType, ObjectType
from app.schemas.feedback_selection import bound_selection, build_passages, to_quoted
from app.schemas.playground import PlaygroundReply, PlaygroundRequest
from app.schemas.starter import VERSION as STARTER_VERSION
from app.schemas.starter import StarterPlan

logger = logging.getLogger(__name__)

VERSION = "playground.tutor.v14"


async def validate_lesson_origin(
    db: AsyncSession, learner_id: str, body: PlaygroundRequest
) -> None:
    if body.lesson_origin is None:
        return
    # Read columns rather than a potentially stale ORM identity-map object.
    row = (
        await db.execute(
            select(Session.ended_at).where(
                Session.id == body.session_id, Session.learner_id == learner_id
            )
        )
    ).one_or_none()
    if row is None or row[0] is not None:
        raise AppError("not_found", "Start or resume a session to use the tutor.", 404)
    checkpoint = await db.scalar(
        select(SessionCheckpoint.packet_json)
        .where(
            SessionCheckpoint.session_id == body.session_id,
            SessionCheckpoint.learner_id == learner_id,
            SessionCheckpoint.expires_at > utcnow_iso(),
        )
        .order_by(SessionCheckpoint.ts.desc(), SessionCheckpoint.id.desc())
        .limit(1)
    )
    skill = body.lesson_origin.skill_id
    if (
        not checkpoint
        or checkpoint.get("skill_id") != skill
        or not await db.scalar(select(SkillNode.id).where(SkillNode.id == skill))
    ):
        raise AppError(
            "lesson_context_changed",
            "This lesson context has changed. Return to the lesson before asking again; your code draft is unchanged.",
            409,
        )


def messages(
    body: PlaygroundRequest,
    historical: dict[str, Any] | None = None,
    memory: list[dict[str, str]] | None = None,
    evidence: LessonEvidence | None = None,
) -> list[Message]:
    workspace = body.model_dump(
        exclude={
            "session_id",
            "lesson_origin",
            "question",
            "intent",
            "learning_context",
            "learner_question",
            "prefer_saved",
            "questioning_style",
        }
    )
    if evidence is not None:
        workspace["lesson_contract"] = {"title": evidence.title, "goal": evidence.goal}
    if body.intent == "check_answer":
        workspace["answer_passages"] = build_passages(body.learner_answer or "")
    if body.output_stale:
        workspace["output"] = ""
        workspace["historical_execution_output"] = body.output
    if historical is not None:
        workspace["historical_answer"] = historical
    if memory:
        # Provenance IDs belong in saved metadata/UI, not model-visible source citations.
        workspace["previous_answers"] = [
            {key: value for key, value in item.items() if key != "answer_id"} for item in memory
        ]
    arithmetic = checks_for(body)
    bins = bin_checks_for(body)
    if bins:
        # Labels remain untrusted workspace data, never trusted system instructions.
        workspace["conditional_bin_checks"] = [asdict(check) for check in bins]
    data = escape_data(json.dumps(workspace, ensure_ascii=False))
    packet = [
        Message(
            role="system",
            content=prompts.base_policy()
            + "\n\n"
            + prompts.playground_task(grounded=evidence is not None)
            + (
                "\nApplication evidence state: the workspace client marks output stale. No current execution output "
                "is supplied. historical_execution_output belongs to an earlier code state and "
                "cannot establish results, counts or success of the current code. Explain static "
                "code behavior and answer conceptual questions normally; if current execution "
                "results matter, ask the learner to rerun the current cell. Do not treat stale "
                "output as proof merely because it agrees with the learner's claim."
                if body.output_stale
                else (
                    "\nApplication evidence state: output is client-supplied and not marked stale; "
                    "the app has not independently verified its execution or correspondence to this code."
                    if body.output
                    else "\nApplication evidence state: no execution output is supplied. "
                    "This does not establish whether the code ran; explain static behavior without claiming execution."
                )
            )
            + (
                "\nThe application computed these literal arithmetic identities locally. "
                "Use them to explain calculation errors; do not imply the whole answer is checked. "
                "A false equality may be quoted or rejected by the learner: do not infer endorsement.\n"
                + summary(arithmetic)
                if arithmetic
                else ""
            )
            + (
                "\nThe application derived the following conditional bin-boundary facts from literal "
                "arguments. Use these facts within their stated assumptions; never claim execution. "
                "If the learner's boundary claim contradicts these facts, mark it needs_revision, "
                "not supported. Bin 1 means the first label (index 0), bin 2 the second (index 1). "
                "Do not confuse the exercise's desired intervals with the intervals of the current code.\n"
                + bin_summary(bins)
                if bins
                else ""
            )
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
            )
            + (
                "\nThe learner explicitly requests a proposed correction. Reconsider the earlier answer "
                "and the learner report; the report is not proof. State what should change and why, "
                "or explain why the earlier reasoning still holds. Separate supported reasoning from "
                "uncertainty and identify evidence still needed. Do not invent fresh source checks or "
                "execution, call the result verified, or imply the original was replaced."
                if historical is not None and historical.get("purpose") == "correction"
                else ""
            ),
        ),
        Message(
            role="user",
            content=(
                '<workspace_data note="quoted untrusted data">\n'
                + data
                + "\n</workspace_data>\n"
                + (evidence.quoted_passages() + "\n" if evidence is not None else "")
                + "Selected questioning_style: "
                + body.questioning_style
                + "\nCurrent request ("
                + body.intent
                + "): "
                + body.question
            ),
        ),
    ]

    if body.intent == "check_answer":
        packet[0] = packet[0].model_copy(
            update={"content": packet[0].content + "\n\n" + prompts.answer_feedback_task()}
        )
    if body.intent == "starter":
        packet[0] = packet[0].model_copy(
            update={"content": packet[0].content + "\n\n" + prompts.starter_task()}
        )
    return packet


async def respond(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    body: PlaygroundRequest,
    *,
    historical: dict[str, Any] | None = None,
    settings: Settings | None = None,
    parent_metadata: dict[str, Any] | None = None,
    recovery: AnswerRecovery | None = None,
    repo: RetrievalRepository | None = None,
    on_token: Callable[[str], Awaitable[None]] | None = None,
) -> PlaygroundReply:
    await validate_lesson_origin(db, learner_id, body)
    session = await ksession.get(db, body.session_id)
    if session.learner_id != learner_id or session.ended_at:
        raise AppError("not_found", "Start or resume a session to use the tutor.", http_status=404)
    evidence = None
    retrieval_trace_id = None
    lesson_lookup = (
        body.lesson_origin is not None and historical is None and body.intent != "check_bins"
    )
    if lesson_lookup and repo is not None:
        assert body.lesson_origin is not None
        node = await db.get(SkillNode, body.lesson_origin.skill_id)
        assert node is not None
        lo = await skill_graph.learning_object_for(db, node.id)
        goal = lo.goal if lo else node.description or node.title
        try:
            result = await asyncio.wait_for(
                tools.retrieve(
                    repo,
                    f"{node.title}: {body.learner_question or body.question}",
                    skill_id=node.id,
                    course=node.course,
                    k=6,
                ),
                timeout=5.0,
            )
        except (httpx.HTTPError, ProviderError, NoModelReady, TimeoutError, ValueError) as exc:
            logger.warning("Lesson retrieval unavailable: %s", type(exc).__name__)
        else:
            evidence = evidence_snapshot(result, skill_id=node.id, title=node.title, goal=goal)
            trace = await write_retrieval_trace(
                db,
                result.trace.model_copy(
                    update={
                        "learner_id": learner_id,
                        "session_id": session.id,
                    }
                ),
            )
            retrieval_trace_id = trace.id
        await validate_lesson_origin(db, learner_id, body)
    evidence_identity = evidence.identity() if evidence else None
    prompt_version = VERSION + ".lesson.v2" if evidence is not None else VERSION
    if body.intent == "starter":
        prompt_version += "." + STARTER_VERSION
    source_status: Literal["supplied", "empty", "unavailable", "not_requested"] = (
        "supplied"
        if evidence and evidence.passages
        else "empty"
        if evidence
        else "unavailable"
        if lesson_lookup
        else "not_requested"
    )
    source_values = (
        [
            {"chunk_id": p.chunk_id, "citation": p.citation, "text": p.text}
            for p in evidence.passages
        ]
        if evidence
        else []
    )
    source_note = (
        "Reference passages supplied from local material; they do not verify this answer or code execution."
        if source_values
        else "No matching reference passages supplied; general coding guidance."
        if evidence
        else "Local reference lookup unavailable; general coding guidance."
        if lesson_lookup
        else None
    )
    if body.prefer_saved and historical is None and (not lesson_lookup or evidence is not None):
        try:
            async with db.begin_nested():
                saved = await exact_saved(
                    db, learner_id, body, prompt_version, evidence_identity=evidence_identity
                )
            if saved is not None:
                await validate_lesson_origin(db, learner_id, body)
                return PlaygroundReply(
                    source_status=source_status,
                    sources=source_values,
                    text=saved.text,
                    model=str(saved.metadata_json.get("model", "unknown")),
                    route=str(saved.metadata_json.get("route", "unknown")),
                    turn_id=saved.turn_id,
                    answer_id=saved.id,
                    reused=True,
                    saved_at=saved.created_at,
                    source_note=(
                        (source_note + " Reopened an identical saved reply; no new model call.")
                        if source_note
                        else "Reopened a saved reply for identical supplied context. "
                        "No model call or new checks; external files and datasets may have changed."
                    ),
                )
        except SQLAlchemyError as exc:
            logger.warning("Saved answer reuse unavailable: %s", type(exc).__name__)
    if body.intent == "check_bins":
        bins = bin_checks_for(body)
        if bins:
            return await respond_bins(db, learner_id, body, bins, prompt_version, recovery=recovery)
        raise AppError(
            "unsupported_bin_check",
            "No supported literal pd.cut or pandas.cut call was found. Use a top-level call "
            "with literal numeric bin edges and literal options, or ask the tutor to explain "
            "the code. No model was called and no code was executed.",
            http_status=422,
        )
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
    packet = messages(body, historical, memory, evidence)
    events = EventWriter(db, ksession.event_context(session, activity=ActivityType.CHAT))
    await events.emit(
        Verb.ASKED, ObjectType.TURN, turn_id, context={"text_len": len(body.question)}
    )
    feedback_schema = (
        bound_selection(body.learner_answer or "", socratic=body.questioning_style == "socratic")
        if body.intent == "check_answer"
        else None
    )
    checked_feedback = None
    selected_feedback = None
    starter_plan = None
    await validate_lesson_origin(db, learner_id, body)
    try:
        if on_token is not None and body.intent in {"explain", "hint", "chat"}:
            out = await gateway.complete_streamed(
                TaskClass.HINT if body.intent == "hint" else TaskClass.EXPLAIN_SIMPLE,
                packet,
                on_token=on_token,
                learner_id=learner_id,
                session_id=session.id,
                max_tokens=900,
                temperature=0.2,
                metadata={
                    "task": "playground",
                    "prompt_version": prompt_version,
                    "turn_id": turn_id,
                },
            )
        else:
            out = await gateway.complete(
                TaskClass.ANSWER_FEEDBACK
                if feedback_schema
                else (TaskClass.HINT if body.intent == "hint" else TaskClass.EXPLAIN_SIMPLE),
                packet,
                learner_id=learner_id,
                session_id=session.id,
                max_tokens=650 if feedback_schema else 900,
                response_model=StarterPlan if body.intent == "starter" else feedback_schema,
                metadata={
                    "task": "playground",
                    "prompt_version": prompt_version,
                    "turn_id": turn_id,
                },
            )
        if body.intent == "starter":
            starter_plan = StarterPlan.model_validate_json(out.result.text)
        if feedback_schema:
            selected_feedback = feedback_schema.model_validate_json(out.result.text)
            checked_feedback = to_quoted(
                body.learner_answer or "",
                selected_feedback,
                socratic=body.questioning_style == "socratic",
            )
    except OutputLimitError as exc:
        raise AppError(
            "tutor_output_limit",
            "The reply reached the model's output limit. The received text is incomplete and was not "
            "saved as a completed answer. Keep a copy; use Start different work to ask a shorter question.",
            http_status=503,
        ) from exc
    except (GatewayError, ValidationError, NoModelReady) as exc:
        raise AppError(
            "tutor_unavailable",
            (
                "The tutor could not provide a usable starter template. Your code is unchanged. "
                "You can ask for an explanation or start a new request."
            )
            if body.intent == "starter"
            else "The tutor is unavailable. Your work is retained; check the selected model and budget, then retry.",
            http_status=503,
        ) from exc
    if not out.result.text.strip():
        raise AppError(
            "tutor_unavailable", "The tutor returned no answer. Try again.", http_status=503
        )
    response_text, citation_warning = disclose(
        starter_plan.render()
        if starter_plan
        else render_feedback(checked_feedback)
        if checked_feedback
        else out.result.text,
        source_count=len(source_values),
        grounded=evidence is not None,
    )
    arithmetic = checks_for(body)
    response_text = disclose_arithmetic(response_text, arithmetic)
    bins = bin_checks_for(body)
    response_text = disclose_bins(response_text, bins)
    if body.output_stale:
        response_text = (
            "Output context: the supplied output is marked outdated and does not verify "
            "the current code. To check current execution results, rerun the current cell.\n\n"
            + response_text
        )
    await write_tutor_trace(
        db,
        TutorTraceRecord(
            learner_id=learner_id,
            session_id=session.id,
            turn_id=turn_id,
            action="playground_" + body.intent,
            prompt_version=prompt_version,
            sections={"workspace": len(packet[1].content) // 4},
            model_call_id=out.model_call_id,
            retrieval_trace_id=retrieval_trace_id,
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
            "prompt_version": prompt_version,
        },
    )
    answer_id = None
    save_error = None
    save_receipt = None
    snapshot: dict[str, Any] = dict(
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
            "prompt_version": prompt_version,
            "model_call_id": out.model_call_id,
            "source_status": source_status,
            "sources": source_values,
            "source_text_hashes": evidence.text_hashes() if evidence else {},
            "lesson_evidence_identity": evidence_identity,
            "lesson_evidence": evidence.model_dump() if evidence else None,
            "starter_plan": starter_plan.model_dump() if starter_plan else None,
            "starter_contract": STARTER_VERSION if starter_plan else None,
            "citation_warning": citation_warning,
            **(
                {"raw_model_text": out.result.text}
                if citation_warning or arithmetic or bins or checked_feedback
                else {}
            ),
            **({"quoted_feedback": checked_feedback.model_dump()} if checked_feedback else {}),
            **(
                {
                    "feedback_selection": selected_feedback.model_dump(),
                    "answer_passages": build_passages(body.learner_answer or ""),
                }
                if selected_feedback
                else {}
            ),
            "arithmetic_checks": [asdict(check) for check in arithmetic],
            "arithmetic_checker_version": ARITHMETIC_VERSION,
            "bin_checks": [asdict(check) for check in bins],
            "bin_checker_version": BIN_VERSION,
            "answer_memory": memory,
            "execution_evidence_state": "stale_client_output"
            if body.output_stale
            else ("unverified_client_output" if body.output else "no_output"),
            "context_scope": "saved_answer_followup"
            if historical
            else "lesson_reference_snapshot"
            if evidence is not None
            else "supplied_workspace_only",
            **(parent_metadata or {}),
            "learning_context": body.learning_context.model_dump()
            if body.learning_context
            else None,
        },
    )
    try:
        answer = await save_completed(db, **snapshot)
        answer_id = answer.id
    except SQLAlchemyError as exc:
        # Do not log SQL parameters: they can contain private learner text/code.
        logger.warning("Tutor answer save failed: %s", type(exc).__name__)
        if recovery is not None:
            save_receipt = recovery.issue(snapshot)
        save_error = "This answer could not be saved to the database. Keep a copy before leaving."
    return PlaygroundReply(
        source_status=source_status,
        sources=source_values,
        text=response_text,
        model=out.registry_id,
        route=out.route,
        turn_id=turn_id,
        answer_id=answer_id,
        save_error=save_error,
        save_receipt=save_receipt,
        source_note=source_note
        or (
            "Used previous tutor replies as unverified context; no course sources or execution checked."
            if memory
            else "Feedback on supplied work; no course sources or execution checked."
            if checked_feedback
            else "General coding guidance; no course sources retrieved."
        ),
        memory_answers=[item["answer_id"] for item in memory],
    )
