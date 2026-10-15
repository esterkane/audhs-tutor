"""Owned immutable proposal receipts, separate from teaching answers and acceptance."""

from typing import Any

from sqlalchemy import JSON, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import ask_requests
from app.db.models import AskRequest
from app.db.workspace_requests import request_fingerprint
from app.orchestrator.answer_check_binding import text_hash
from app.orchestrator.ask_context_binding import validate_references
from app.orchestrator.ask_context_inputs import ProposalInputs
from app.schemas.ask import AskSources, ConversationBrief
from app.schemas.ask_context_proposals import ContextProposal, InputProvenance, ProposalReceipt


def request_payload(
    parent: str, area: str | None, brief: ConversationBrief, sources: AskSources | None
) -> dict[str, Any]:
    return {
        "operation": "context_proposal.v1",
        "parent_answer_id": parent,
        "area_id": area,
        "brief": ConversationBrief.model_validate(brief.model_dump()).model_dump(),
        "sources": AskSources.model_validate(sources.model_dump()).model_dump()
        if sources
        else None,
    }


def parse_receipt(identity: str, raw: dict[str, Any]) -> ProposalReceipt:
    receipt = ProposalReceipt.model_validate(raw)
    if receipt.proposal_id != identity:
        raise AppError("context_invalid", "The saved proposal identity does not match.", 409)
    return receipt


async def replay(
    db: AsyncSession, learner_id: str, key: str, payload: dict[str, Any]
) -> ProposalReceipt | None:
    if payload.get("operation") != "context_proposal.v1":
        raise ValueError("Wrong proposal operation")
    result = await ask_requests.replay(db, learner_id, key, payload)
    return parse_receipt(result[0], result[1]) if result else None


async def complete(
    db: AsyncSession,
    learner_id: str,
    identity: str,
    payload: dict[str, Any],
    inputs: ProposalInputs,
    proposal: ContextProposal,
) -> ProposalReceipt:
    """Caller resolves inputs and claims identity before generation; commits afterward.

    No model is called here. Completion cannot overwrite a stored receipt. All input
    provenance is retained, including unquoted inputs which may influence paraphrases.
    """
    if payload.get("operation") != "context_proposal.v1":
        raise ValueError("Wrong proposal operation")
    brief = ConversationBrief.model_validate(payload["brief"])
    selection = AskSources.model_validate(payload["sources"]) if payload["sources"] else None
    expected_sources = selection.passage_hashes if selection else {}
    actual_sources = {
        item.record_id: text_hash(item.text)
        for item in inputs.inputs.values()
        if item.origin == "selected_source"
    }
    if expected_sources != actual_sources:
        raise AppError(
            "context_changed", "Selected proposal sources do not match the request.", 409
        )
    if (
        payload["parent_answer_id"] != inputs.parent_answer_id
        or payload["area_id"] != inputs.area_id
        or text_hash(brief.model_dump_json()) != inputs.brief_hash
    ):
        raise AppError("context_changed", "Proposal inputs do not match the requested notes.", 409)
    checked = validate_references(proposal, inputs.inputs)
    receipt = ProposalReceipt(
        proposal_id=identity,
        parent_answer_id=inputs.parent_answer_id,
        area_id=inputs.area_id,
        base_brief_hash=inputs.brief_hash,
        inputs={
            key: InputProvenance(
                record_id=item.record_id,
                version_hash=item.version_hash,
                text_hash=text_hash(item.text),
                characters=len(item.text),
                origin=item.origin,
            )
            for key, item in inputs.inputs.items()
        },
        proposal=checked,
    )
    updated = await db.scalar(
        update(AskRequest)
        .where(
            AskRequest.id == identity,
            AskRequest.learner_id == learner_id,
            AskRequest.fingerprint == request_fingerprint(payload),
            or_(AskRequest.response_json.is_(None), AskRequest.response_json == JSON.NULL),
        )
        .values(response_json=receipt.model_dump(mode="json"))
        .returning(AskRequest.id)
    )
    if updated is None:
        raise AppError("context_unavailable", "The proposal was already completed or removed.", 409)
    return receipt


async def owned(db: AsyncSession, learner_id: str, identity: str) -> ProposalReceipt:
    row = await db.scalar(
        select(AskRequest)
        .where(
            AskRequest.id == identity,
            AskRequest.learner_id == learner_id,
        )
        .execution_options(populate_existing=True)
    )
    if row is None or row.response_json is None:
        raise AppError("not_found", "This completed proposal is unavailable.", 404)
    return parse_receipt(row.id, row.response_json)
