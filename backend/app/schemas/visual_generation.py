"""Model supplies presentation only; identity and provenance remain server-owned."""

from pydantic import Field, model_validator

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
