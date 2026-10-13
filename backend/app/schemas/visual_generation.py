"""Model supplies presentation only; identity and provenance remain server-owned."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.answer_visual_binding import AnswerVisualBinding
from app.schemas.visual_binding import Identifier
from app.schemas.visual_relationship import (
    Caption,
    GraphPart,
    RelationshipEdge,
    RelationshipNode,
    validate_graph,
)


class GraphProposal(GraphPart):
    title: Caption
    text_equivalent: str = Field(min_length=1, max_length=8000)
    directed: bool
    source_chunk_ids: tuple[Identifier, ...] = Field(default=(), max_length=64)
    nodes: tuple[RelationshipNode, ...] = Field(min_length=1, max_length=16)
    edges: tuple[RelationshipEdge, ...] = Field(max_length=32)

    @model_validator(mode="after")
    def references(self) -> "GraphProposal":
        if len(set(self.source_chunk_ids)) != len(self.source_chunk_ids):
            raise ValueError("duplicate source reference")
        validate_graph(self.nodes, self.edges, set(self.source_chunk_ids), "unknown graph source")
        return self


# Public projections exclude worker tokens, input fingerprints and raw source snapshots.
class StartVisualGeneration(GraphPart):
    binding: AnswerVisualBinding


class VisualGenerationStatus(BaseModel):
    id: str
    answer_id: str
    state: Literal["pending", "running", "completed", "failed", "cancelled", "interrupted"]
    attempts: int
    attempt_limit: int
    document_id: str | None
    result_version_id: str | None
    error_code: str | None
    created_at: str
    updated_at: str
