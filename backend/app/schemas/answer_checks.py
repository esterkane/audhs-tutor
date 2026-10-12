"""Bounded model review proposals; binding and factual correctness are separate gates."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class PassageEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passage_id: str = Field(min_length=1, max_length=128)
    quote: str = Field(min_length=1, max_length=2000)


class ClaimReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_quote: str = Field(min_length=1, max_length=2000)
    verdict: Literal["supported", "contradicted", "insufficient"]
    explanation: str = Field(min_length=1, max_length=2000)
    evidence: list[PassageEvidence] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def evidence_required(self) -> "ClaimReview":
        if not self.claim_quote.strip() or not self.explanation.strip():
            raise ValueError("Claim and explanation must contain text")
        if self.verdict != "insufficient" and not self.evidence:
            raise ValueError("Support or contradiction requires cited passage evidence")
        if any(not item.quote.strip() for item in self.evidence):
            raise ValueError("Evidence quotation must contain text")
        return self


class AnswerReviewProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ClaimReview] = Field(min_length=1, max_length=12)
    limitations: list[
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    ] = Field(default_factory=list, max_length=12)


class SavedAnswerReview(BaseModel):
    """Server-issued binding receipt, never a user assertion of factual verification."""

    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    method: Literal["local_model_review"] = "local_model_review"
    coverage: Literal["listed_claims_only"] = "listed_claims_only"
    answer_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    passage_hashes: dict[str, str] = Field(max_length=24)
    proposal: AnswerReviewProposal

    @model_validator(mode="after")
    def valid_passage_hashes(self) -> "SavedAnswerReview":
        for key, value in self.passage_hashes.items():
            if not key.strip() or len(key) > 128:
                raise ValueError("Invalid passage identity")
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("Invalid passage hash")
        return self


class AnswerCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer_id: str = Field(min_length=1, max_length=128)
    passage_ids: list[Annotated[str, StringConstraints(min_length=1, max_length=128)]] = Field(
        min_length=1, max_length=6
    )

    passage_hashes: dict[str, Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]] = Field(
        max_length=6
    )

    @model_validator(mode="after")
    def distinct_passages(self) -> "AnswerCheckRequest":
        if len(set(self.passage_ids)) != len(self.passage_ids):
            raise ValueError("Choose each passage only once")
        if set(self.passage_hashes) != set(self.passage_ids):
            raise ValueError("Each selected passage requires its displayed-text hash")
        return self


class CheckedPassageStatus(BaseModel):
    passage_id: str
    title: str | None = None
    document_version: int | None = None
    newer_version_available: bool = False
    binding_status: Literal["unchanged", "changed", "missing"]


class AnswerCheckDetail(BaseModel):
    id: str
    answer_id: str
    created_at: str
    method: Literal["local_model_review"] = "local_model_review"
    coverage: Literal["listed_claims_only"] = "listed_claims_only"
    binding_status: Literal["unchanged", "changed_or_missing", "invalid_record"]
    proposal: AnswerReviewProposal | None = None
    passages: list[CheckedPassageStatus] = Field(default_factory=list)
    note: str = "Local model review of listed claims only; not independent factual verification."


class AnswerCheckPage(BaseModel):
    items: list[AnswerCheckDetail]
    has_more: bool = False
