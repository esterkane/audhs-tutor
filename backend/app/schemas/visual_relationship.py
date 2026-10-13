"""Non-executable relationship specs, not proof that a diagram teaches correctly.

Renderers must display every string as text, never HTML/Markdown or a URL loader.
Stored authored history, review and ownership are separate lifecycle concerns.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.visual_binding import Identifier, VisualBinding

GraphId = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")]
Caption = Annotated[str, Field(min_length=1, max_length=240)]
MAX_RELATIONSHIP_BYTES = 131_072


class GraphPart(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class RelationshipNode(GraphPart):
    id: GraphId
    label: Caption
    explanation: str = Field(min_length=1, max_length=1200)
    source_chunk_ids: tuple[Identifier, ...] = Field(default=(), max_length=16)


class RelationshipEdge(GraphPart):
    id: GraphId
    source: GraphId
    target: GraphId
    label: Caption
    source_chunk_ids: tuple[Identifier, ...] = Field(default=(), max_length=16)


class RelationshipVisual(GraphPart):
    schema_version: Literal["visual.v1"]
    kind: Literal["relationship"]
    binding: VisualBinding
    title: Caption
    text_equivalent: str = Field(min_length=1, max_length=8000)
    directed: bool
    nodes: tuple[RelationshipNode, ...] = Field(min_length=1, max_length=64)
    edges: tuple[RelationshipEdge, ...] = Field(max_length=128)

    @model_validator(mode="after")
    def check_references(self) -> "RelationshipVisual":
        validate_graph(
            self.nodes,
            self.edges,
            {source.chunk_id for source in self.binding.sources},
            "part source is absent from lesson binding",
        )
        return self


def parse_relationship(raw: bytes) -> RelationshipVisual:
    """Bound the complete transport payload before JSON parsing.

    Production adapters must use this boundary (and cap the incoming request body),
    then resolve/check binding records and review semantics before accepting content.
    """
    if len(raw) > MAX_RELATIONSHIP_BYTES:
        raise ValueError("relationship payload exceeds byte limit")
    return RelationshipVisual.model_validate_json(raw)


def validate_graph(
    nodes: tuple[RelationshipNode, ...],
    edges: tuple[RelationshipEdge, ...],
    source_ids: set[str],
    source_error: str,
) -> None:
    """Shared bounded topology checks; target membership is resolved separately."""
    ids = {node.id for node in nodes}
    if len(ids) != len(nodes):
        raise ValueError("duplicate node id")
    if len({edge.id for edge in edges}) != len(edges):
        raise ValueError("duplicate edge id")
    if any(edge.source not in ids or edge.target not in ids for edge in edges):
        raise ValueError("edge endpoint does not exist")
    parts: tuple[RelationshipNode | RelationshipEdge, ...] = (*nodes, *edges)
    for part in parts:
        if len(set(part.source_chunk_ids)) != len(part.source_chunk_ids):
            raise ValueError("duplicate part source reference")
        if not set(part.source_chunk_ids) <= source_ids:
            raise ValueError(source_error)
    # Cycles, isolated nodes, self-loops and labeled parallel edges can be meaningful.
