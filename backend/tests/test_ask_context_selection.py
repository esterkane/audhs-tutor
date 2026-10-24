"""Server ranges eliminate offset guessing, never certify a paraphrase."""

import pytest
from pydantic import ValidationError

from app.orchestrator.answer_check_binding import text_hash
from app.orchestrator.ask_context_binding import ContextInput, bind_selection
from app.schemas.ask_context_proposals import ProposalSelection


def selection(ids, value="A learner claim, not a fact"):
    return ProposalSelection.model_validate(
        {
            "changes": [
                {"field": "notes", "value": value, "rationale": "Keep this claim", "input_ids": ids}
            ]
        }
    )


def test_server_binds_original_unicode_text_and_returns_detached_proposal():
    text = 'A 🧠 claim <tag> with "quotes".'
    inputs = {"Q1": ContextInput(text, "learner_statement", "record", text_hash(text))}
    draft = selection(["Q1"])
    bound = bind_selection(draft, inputs)
    reference = bound.changes[0].references[0]
    assert (reference.start, reference.end, reference.text_hash) == (0, len(text), text_hash(text))
    draft.changes[0].value = "Changed afterward"
    assert bound.changes[0].value != draft.changes[0].value


@pytest.mark.parametrize("text", ["", "   ", "x" * 24001])
async def test_unusable_input_rejected(text):
    with pytest.raises(ValueError):
        bind_selection(selection(["Q1"]), {"Q1": ContextInput(text, "learner_statement", "r", "v")})


def test_unknown_and_duplicate_ids_rejected():
    with pytest.raises(ValueError):
        bind_selection(selection(["missing"]), {})
    with pytest.raises(ValidationError):
        selection(["Q1", "Q1"])


def test_binding_is_not_semantic_support():
    text = "A byte has eight bits."
    result = bind_selection(
        selection(["Q1"], "All missing data should be deleted."),
        {"Q1": ContextInput(text, "learner_statement", "r", text_hash(text))},
    )
    assert result.changes[0].value == "All missing data should be deleted."


def test_mutated_selection_is_revalidated():
    draft = selection(["Q1"])
    draft.changes[0].input_ids = []
    with pytest.raises(ValidationError):
        bind_selection(draft, {})
