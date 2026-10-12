import pytest
from pydantic import ValidationError

from app.orchestrator.answer_check_binding import bind_review
from app.schemas.answer_checks import AnswerReviewProposal


def proposal(**changes):
    claim = dict(
        claim_quote="Eight bits are one byte.",
        verdict="supported",
        explanation="The passage states this relationship.",
        evidence=[dict(passage_id="p1", quote="one byte has eight bits")],
    )
    claim.update(changes)
    return AnswerReviewProposal(claims=[claim])


ANSWER = "Eight bits are one byte. A separate claim remains unchecked."
PASSAGES = {"p1": "Here one byte has eight bits; this is the definition."}


def test_exact_binding_invalidates_changed_or_deleted_inputs():
    result = bind_review(ANSWER, PASSAGES, proposal())
    assert result.matches(ANSWER, PASSAGES)
    assert not result.matches(ANSWER + " Edited", PASSAGES)
    assert not result.matches(ANSWER, {})
    assert not result.matches(ANSWER, {"p1": PASSAGES["p1"] + " Revised"})
    assert result.matches(ANSWER, {**PASSAGES, "unused": "Other material"})


@pytest.mark.parametrize(
    "changes",
    [
        {"claim_quote": "Sixteen bits are one byte."},
        {"evidence": [dict(passage_id="invented", quote="one byte has eight bits")]},
        {"evidence": [dict(passage_id="p1", quote="the answer has been verified")]},
    ],
)
def test_invented_claims_and_citations_are_rejected(changes):
    with pytest.raises(ValueError):
        bind_review(ANSWER, PASSAGES, proposal(**changes))


def test_uncertainty_needs_no_fabricated_evidence():
    result = bind_review(ANSWER, {}, proposal(verdict="insufficient", evidence=[]))
    assert result.proposal.claims[0].verdict == "insufficient"
    with pytest.raises(ValidationError):
        proposal(evidence=[])


def test_binding_is_not_semantic_verification_and_copies_proposal():
    raw = proposal(verdict="contradicted")
    result = bind_review(ANSWER, PASSAGES, raw)
    # Exact citations do not prove the model's verdict. Preserve it as a proposal.
    assert result.proposal.claims[0].verdict == "contradicted"
    raw.claims.clear()
    assert len(result.proposal.claims) == 1


def test_duplicate_claims_and_unknown_fields_rejected():
    raw = proposal()
    raw.claims.append(raw.claims[0])
    with pytest.raises(ValueError, match="Duplicate"):
        bind_review(ANSWER, PASSAGES, raw)
    with pytest.raises(ValidationError):
        proposal(verified=True)


def test_uncited_supplied_passages_remain_part_of_check_lineage():
    supplied = {**PASSAGES, "counterexample": "Additional context considered by reviewer"}
    result = bind_review(ANSWER, supplied, proposal())
    assert not result.matches(ANSWER, PASSAGES)
    assert not result.matches(ANSWER, {**supplied, "counterexample": "Changed"})


@pytest.mark.parametrize("value", ["", "   ", "x" * 2001])
def test_limitation_text_is_nonblank_and_bounded(value):
    raw = proposal().model_dump()
    raw["limitations"] = [value]
    with pytest.raises(ValidationError):
        AnswerReviewProposal.model_validate(raw)


def test_serialized_review_revalidates_version_and_exact_quotes():
    import json

    from app.orchestrator.answer_check_binding import load_bound_review

    result = bind_review(ANSWER, PASSAGES, proposal())
    raw = json.loads(result.receipt_json)
    raw["version"] = 2
    with pytest.raises(ValueError):
        load_bound_review(json.dumps(raw), ANSWER, PASSAGES)
    raw["version"] = 1
    raw["proposal"]["claims"][0]["claim_quote"] = "Invented claim"
    with pytest.raises(ValueError):
        load_bound_review(json.dumps(raw), ANSWER, PASSAGES)
    detached = result.proposal
    detached.claims.clear()
    assert len(result.proposal.claims) == 1
