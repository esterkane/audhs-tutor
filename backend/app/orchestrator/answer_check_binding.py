"""Bind proposed checks to exact supplied text; never treat this as truth verification."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from app.schemas.answer_checks import AnswerReviewProposal, SavedAnswerReview


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BoundReview:
    # Keep only an immutable serialized receipt. Accessors return validated copies.
    receipt_json: str

    @property
    def proposal(self) -> AnswerReviewProposal:
        return SavedAnswerReview.model_validate_json(self.receipt_json).proposal

    def matches(self, answer: str, passages: Mapping[str, str]) -> bool:
        """Revalidate persisted structure, exact quotations and all input hashes."""
        try:
            load_bound_review(self.receipt_json, answer, passages)
        except ValueError:
            return False
        return True


def load_bound_review(raw: str, answer: str, passages: Mapping[str, str]) -> BoundReview:
    receipt = SavedAnswerReview.model_validate_json(raw)
    if receipt.answer_hash != text_hash(answer):
        raise ValueError("Answer changed after review")
    selected = {}
    for key, digest in receipt.passage_hashes.items():
        if key not in passages or text_hash(passages[key]) != digest:
            raise ValueError("Source passage changed or is unavailable")
        selected[key] = passages[key]
    # Hash matches alone cannot certify a malformed or edited stored proposal.
    return bind_review(answer, selected, receipt.proposal)


def bind_review(
    answer: str, passages: Mapping[str, str], proposal: AnswerReviewProposal
) -> BoundReview:
    """Reject invented quotations/IDs. Inputs come from the server-owned snapshot.

    Exact substrings intentionally reject normalized or paraphrased quotations.
    Partial claim coverage is allowed and must be disclosed by the presentation.
    Even matching evidence can be irrelevant or misleading: entailment remains a
    separate model/human review, not a claim made by this deterministic gate.
    """
    # Even uncited supplied passages may have influenced the review.
    hashes = {key: text_hash(value) for key, value in passages.items()}
    proposal = AnswerReviewProposal.model_validate(proposal.model_dump())
    seen: set[str] = set()
    for claim in proposal.claims:
        if claim.claim_quote not in answer:
            raise ValueError("Claim quotation is absent from the answer snapshot")
        if claim.claim_quote in seen:
            raise ValueError("Duplicate claim quotation")
        seen.add(claim.claim_quote)
        for evidence in claim.evidence:
            passage = passages.get(evidence.passage_id)
            if passage is None or evidence.quote not in passage:
                raise ValueError("Evidence is absent from the supplied passage snapshot")
    receipt = SavedAnswerReview(
        answer_hash=text_hash(answer), passage_hashes=hashes, proposal=proposal
    )
    return BoundReview(json.dumps(receipt.model_dump(mode="json"), sort_keys=True))
