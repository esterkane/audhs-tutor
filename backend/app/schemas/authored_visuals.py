"""Bounded non-executable authoring commands; no lesson evidence is fabricated for Ask."""

from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from app.schemas.answer_visual_binding import AnswerVisualBinding, Digest
from app.schemas.visual_binding import BindingPart, Identifier
from app.schemas.visual_relationship import (
    MAX_RELATIONSHIP_BYTES,
    Caption,
    GraphPart,
    RelationshipEdge,
    RelationshipNode,
    RelationshipVisual,
    validate_graph,
)


class AnswerRelationshipVisual(GraphPart):
    schema_version: Literal["visual.answer.v1"]
    kind: Literal["relationship"]
    binding: AnswerVisualBinding
    title: Caption
    text_equivalent: str = Field(min_length=1, max_length=8000)
    directed: bool
    source_chunk_ids: tuple[Identifier, ...] = Field(default=(), max_length=64)
    nodes: tuple[RelationshipNode, ...] = Field(min_length=1, max_length=64)
    edges: tuple[RelationshipEdge, ...] = Field(max_length=128)

    @model_validator(mode="after")
    def references(self) -> "AnswerRelationshipVisual":
        if len(set(self.source_chunk_ids)) != len(self.source_chunk_ids):
            raise ValueError("duplicate source reference")
        validate_graph(self.nodes, self.edges, set(self.source_chunk_ids), "unknown visual source")
        return self


VisualSpec = Annotated[
    RelationshipVisual | AnswerRelationshipVisual, Field(discriminator="schema_version")
]


class SaveVisual(BindingPart):
    action: Literal["save"]
    document_id: Identifier | None = None
    expected_revision: int = Field(ge=0)
    spec: VisualSpec

    @model_validator(mode="after")
    def revision(self) -> "SaveVisual":
        if (self.document_id is None) != (self.expected_revision == 0):
            raise ValueError(
                "New documents require revision zero; edits require a current revision"
            )
        return self


class ReviewVisual(BindingPart):
    action: Literal["review"]
    document_id: Identifier
    expected_revision: int = Field(ge=1)
    version_id: Identifier
    content_sha256: Digest
    snapshot_sha256: Digest
    decision: Literal["accept", "reject"]
    confirm: Literal[True]
    note: str = Field(default="", max_length=4000)


class ArchiveVisual(BindingPart):
    action: Literal["archive"]
    document_id: Identifier
    expected_revision: int = Field(ge=1)
    archived: bool


VisualCommand = Annotated[SaveVisual | ReviewVisual | ArchiveVisual, Field(discriminator="action")]
COMMAND: TypeAdapter[SaveVisual | ReviewVisual | ArchiveVisual] = TypeAdapter(VisualCommand)
SPEC: TypeAdapter[RelationshipVisual | AnswerRelationshipVisual] = TypeAdapter(VisualSpec)


def parse_command(raw: bytes) -> SaveVisual | ReviewVisual | ArchiveVisual:
    if len(raw) > MAX_RELATIONSHIP_BYTES:
        raise ValueError("visual command exceeds byte limit")
    return COMMAND.validate_json(raw)


class VisualOrigin(BindingPart):
    """Server-supplied generation identity, never a client-provided approval."""

    kind: Literal["learner", "model"] = "learner"
    model: Identifier | None = None
    prompt_version: Identifier | None = None

    @model_validator(mode="after")
    def generation_identity(self) -> "VisualOrigin":
        if self.kind == "model" and (not self.model or not self.prompt_version):
            raise ValueError("Model drafts require model and prompt identity")
        if self.kind == "learner" and (self.model or self.prompt_version):
            raise ValueError("Learner edits have no generation identity")
        return self


class VisualReceipt(BindingPart):
    action: Literal["save", "review", "archive"]
    document_id: Identifier
    revision: int
    version_id: Identifier | None = None
    content_sha256: Digest | None = None
    snapshot_sha256: Digest | None = None
    review_id: Identifier | None = None
    archived: bool = False
