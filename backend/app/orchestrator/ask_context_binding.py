"""Validate proposal references against server-resolved inputs; not semantic truth.

Caller must resolve ownership, branch, selected-source eligibility and versions before
building inputs. This pure boundary has no database access and cannot establish them.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from app.orchestrator.answer_check_binding import text_hash
from app.schemas.ask_context_proposals import (
    ContextProposal,
    ProposalReference,
    ProposalSelection,
    ProposedField,
)


@dataclass(frozen=True)
class ContextInput:
    text: str
    origin: Literal["learner_statement", "unverified_tutor_reply", "selected_source"]
    record_id: str
    version_hash: str


def validate_references(
    proposal: ContextProposal, inputs: Mapping[str, ContextInput]
) -> ContextProposal:
    """Return a revalidated detached proposal; never infer support from matching spans."""
    checked = ContextProposal.model_validate(proposal.model_dump())
    if sum(len(item.text) for item in inputs.values()) > 24000:
        raise ValueError("Context exceeds input bound")
    for change in checked.changes:
        for reference in change.references:
            item = inputs.get(reference.input_id)
            if item is None:
                raise ValueError("Reference was not supplied to this proposal")
            if text_hash(item.text) != reference.text_hash:
                raise ValueError("Referenced text changed")
            if (
                reference.end > len(item.text)
                or not item.text[reference.start : reference.end].strip()
            ):
                raise ValueError("Reference range is outside text or contains only whitespace")
    return checked


def bind_selection(
    selection: "ProposalSelection", inputs: Mapping[str, ContextInput]
) -> ContextProposal:
    """Bind whole selected inputs deterministically; selection is not entailment."""
    checked = ProposalSelection.model_validate(selection.model_dump())
    changes = []
    for change in checked.changes:
        references = []
        for identity in change.input_ids:
            item = inputs.get(identity)
            if item is None:
                raise ValueError("Selected input was not supplied to this proposal")
            references.append(
                ProposalReference(
                    input_id=identity, text_hash=text_hash(item.text), start=0, end=len(item.text)
                )
            )
        changes.append(
            ProposedField(
                field=change.field,
                value=change.value,
                rationale=change.rationale,
                references=references,
            )
        )
    return validate_references(ContextProposal(changes=changes), inputs)
