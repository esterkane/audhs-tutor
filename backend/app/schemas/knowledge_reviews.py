from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AuthoringSetup(BaseModel):
    enabled: bool
    key_configured: bool
    model_id: str
    daily_budget_usd: float
    counted_today_usd: float


class ReviewPolicyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    interval_days: int = Field(default=30, ge=1, le=365)
    urls: list[str] = Field(min_length=1, max_length=3)


class FactFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str = Field(min_length=1, max_length=500)
    verdict: Literal["supported", "needs_revision", "insufficient"]
    source_index: int = Field(ge=1, le=3)
    quote: str = Field(min_length=1, max_length=800)
    explanation: str = Field(min_length=1, max_length=800)


class FactualProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findings: list[FactFinding] = Field(min_length=1, max_length=6)
    proposed_explanation: str = Field(default="", max_length=4000)


class ReviewSource(BaseModel):
    url: str
    sha256: str
    excerpt: str
    fetched_at: str


class ReviewRecord(BaseModel):
    id: str
    draft_id: str
    draft_version: int
    checked_at: str
    outcome: Literal["reviewed", "sources_unchanged", "failed"]
    sources: list[ReviewSource] = Field(default_factory=list)
    proposal: FactualProposal | None = None
    model_call_id: str | None = None
    revision_id: str | None = None
    error: str | None = None
    error_message: str | None = None


class FactualReviewOut(BaseModel):
    id: str
    draft_id: str
    enabled: bool
    interval_days: int
    urls: list[str]
    next_due_at: str
    history: list[ReviewRecord]
