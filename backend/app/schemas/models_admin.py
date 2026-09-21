"""Models settings screen (ADR-0010): registry rows, HF search, jobs, routing table."""

from typing import Any

from pydantic import BaseModel, Field


class ModelRow(BaseModel):
    id: str
    display_name: str
    source: str
    repo_id: str
    file_or_tag: str | None
    runtime: str
    role: str
    quant: str | None
    size_gb: float | None
    context_len: int | None
    licence: str | None
    status: str
    benchmark: dict[str, Any] | None
    price_in_per_mtok: float
    price_out_per_mtok: float
    local_path: str | None
    updated_at: str


class ModelList(BaseModel):
    models: list[ModelRow]


class HfSearchHit(BaseModel):
    repo_id: str
    downloads: int | None
    likes: int | None
    tags: list[str]


class HfSearchOut(BaseModel):
    hits: list[HfSearchHit]


class AddIn(BaseModel):
    source: str
    repo_id: str
    file: str | None = None
    tag: str | None = None
    registry_id: str | None = None
    display_name: str | None = None
    role: str = "chat"
    quant: str | None = None
    context_len: int | None = None
    price_in: float = 0.0
    price_out: float = 0.0


class AssignIn(BaseModel):
    task: str


class JobOut(BaseModel):
    id: str
    kind: str  # pull | bench
    registry_id: str
    status: str  # running | done | failed
    log: list[str] = Field(default_factory=list)
    error: str | None = None
    result: dict[str, Any] | None = None


class JobList(BaseModel):
    jobs: list[JobOut]


class ChainEntry(BaseModel):
    registry_id: str
    status: str


class RouteRow(BaseModel):
    task: str
    override: str | None
    chain: list[ChainEntry]
    resolved: str | None
    problem: str | None = None  # why nothing is ready (P6)
    action: str | None = None  # the one step that would fix it


class RoutingOut(BaseModel):
    profile: str
    routes: list[RouteRow]


class CostBucket(BaseModel):
    key: str
    calls: int
    failed: int
    cost_usd: float
    unknown_usd: float
    tokens_in: int
    tokens_out: int


class CostFailure(BaseModel):
    ts: str
    request_id: str | None
    attempt: int
    registry_id: str
    task: str
    route: str
    outcome: str
    cost_status: str
    reserved_usd: float
    error: str | None


class CostToday(BaseModel):
    counted: float
    remaining: float
    reported: float
    estimated: float
    unknown_reserved: float
    legacy: float
    open_reservations: float


class CostWindow(BaseModel):
    hosted_calls: int
    free_calls: int
    failed_calls: int
    cancelled_calls: int
    blocked_calls: int
    retried_requests: int
    unknown_calls: int
    legacy_rows: int
    open_reservations: int
    expired_reservations: int


class CostsOut(BaseModel):
    """P6 cost view. `today.counted` is what the daily cap sees: reported + estimated + legacy
    hosted cost + unknown calls at their reserved worst case + open reservations."""

    daily_cap_usd: float
    day_start: str
    window_start: str
    today: CostToday
    window: CostWindow
    by_task: list[CostBucket]
    by_provider: list[CostBucket]
    recent_failures: list[CostFailure]
