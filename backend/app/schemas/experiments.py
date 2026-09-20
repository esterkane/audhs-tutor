"""n-of-1 experiments: create from a template or by hand, run, read results as hypotheses."""

from typing import Any

from pydantic import BaseModel, Field


class ArmIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    config: dict[str, Any] = Field(default_factory=dict)


class ExperimentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    hypothesis: str = ""
    metric: str
    unit_type: str = "node"
    arms: list[ArmIn] = Field(min_length=2)


class TemplateIn(BaseModel):
    template: str


class ArmOut(BaseModel):
    id: str
    name: str
    config: dict[str, Any]
    assigned: int


class ExperimentOut(BaseModel):
    id: str
    name: str
    hypothesis: str
    metric: str
    unit_type: str
    status: str
    created_at: str
    started_at: str | None
    ended_at: str | None
    arms: list[ArmOut]


class ExperimentList(BaseModel):
    experiments: list[ExperimentOut]
    templates: list[dict[str, Any]]
    metrics: list[str]


class ArmStatsOut(BaseModel):
    arm_id: str
    name: str
    n: int
    mean: float | None
    sd: float | None


class MetricOut(BaseModel):
    metric: str
    lower_is_better: bool
    arms: list[ArmStatsOut]
    difference: float | None
    ci95: list[float] | None
    reading: str


class ResultsOut(BaseModel):
    experiment: ExperimentOut
    primary_metric: str
    metrics: list[MetricOut]
    units: list[dict[str, Any]]  # per unit: id, arm, label
