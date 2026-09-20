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


class RoutingOut(BaseModel):
    profile: str
    routes: list[RouteRow]
