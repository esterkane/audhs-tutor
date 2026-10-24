"""Explicit local context suggestions; never accepts notes or changes learning state."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import ask_requests
from app.db.traces import TutorTraceRecord, write_tutor_trace
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.orchestrator import ask_context_inputs, ask_context_receipts
from app.orchestrator.ask_context_binding import bind_selection
from app.orchestrator.context import escape_data
from app.orchestrator.prompts import _read
from app.schemas.ask import AskSources, ConversationBrief
from app.schemas.ask_context_proposals import ProposalReceipt, ProposalSelection

PROMPT_VERSION = "ask.context-proposal.v2"


async def suggest(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    parent_answer_id: str,
    area_id: str | None,
    brief: ConversationBrief,
    sources: AskSources | None,
    key: str,
    *,
    quarantine_below_trust: int = 2,
) -> ProposalReceipt:
    """Caller supplies a fresh DB session without unrelated pending writes.

    Gateway transport checks apply to all attempts, including repairs/fallbacks.
    Uncertain/failed requests remain claimed; replay never dispatches another call.
    """
    payload = ask_context_receipts.request_payload(parent_answer_id, area_id, brief, sources)
    previous = await ask_context_receipts.replay(db, learner_id, key, payload)
    if previous:
        return previous
    inputs = await ask_context_inputs.resolve(
        db,
        learner_id,
        parent_answer_id,
        area_id,
        brief,
        sources,
        quarantine_below_trust=quarantine_below_trust,
    )
    identity, completed = await ask_requests.claim(db, learner_id, key, payload)
    if completed:
        return ask_context_receipts.parse_receipt(identity, completed)
    data = {
        "current_notes_unverified": json.loads(inputs.brief_json),
        "older_history_omitted": inputs.older_history_omitted,
        "opening_unavailable": inputs.opening_unavailable,
        "inputs": {
            name: {"text": item.text, "origin": item.origin} for name, item in inputs.inputs.items()
        },
    }
    result = await gateway.complete(
        TaskClass.CHAT,
        [
            Message(role="system", content=_read("ask/context-proposal.v2.md")),
            Message(
                role="user",
                content="<context_data>\n"
                + escape_data(json.dumps(data, ensure_ascii=False))
                + "\n</context_data>",
            ),
        ],
        response_model=ProposalSelection,
        learner_id=learner_id,
        max_tokens=1800,
        metadata={
            "surface": "ask_context_proposal",
            "prompt_version": PROMPT_VERSION,
            "turn_id": identity,
        },
    )
    try:
        proposal = bind_selection(
            ProposalSelection.model_validate(result.result.parsed), inputs.inputs
        )
        current_notes = json.loads(inputs.brief_json)
        proposal.changes = [
            change for change in proposal.changes if change.value != current_notes[change.field]
        ]
        receipt = await ask_context_receipts.complete(
            db, learner_id, identity, payload, inputs, proposal
        )
        await write_tutor_trace(
            db,
            TutorTraceRecord(
                learner_id=learner_id,
                session_id=None,
                turn_id=identity,
                action="ask_context_proposal",
                prompt_version=PROMPT_VERSION,
                model_call_id=result.model_call_id,
                latency_ms=result.result.latency_ms,
            ),
            commit=False,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise AppError(
            "context_output_invalid",
            "The suggestion could not be matched to this conversation. Your notes are unchanged; "
            "this request will not run again automatically.",
            422,
        ) from exc
    except BaseException:
        await db.rollback()
        raise
    return receipt
