"""Normalised intermediate representation shared by every loader (captions, notebooks, PDFs,
markdown, plain text). A loader turns one file into a `SourceDoc`; the chunker turns a `SourceDoc`
into `ChunkDraft`s; the service persists drafts with provenance."""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Literal

BlockKind = Literal["prose", "code", "caption", "slide", "table"]

SOURCE_TYPES = (
    "udemy_caption",
    "transcript",
    "slides",
    "notebook",
    "pdf",
    "markdown",
    "text",
    "document",
    "book",
    "html",
    "code",
    "audio",
    "video",
    "image",
    "manual",
)


@dataclass
class Block:
    text: str
    kind: BlockKind = "prose"
    heading: str | None = None
    t_start: float | None = None
    t_end: float | None = None
    skill_slugs: list[str] = field(default_factory=list)


@dataclass
class SourceDoc:
    title: str
    uri: str
    source_type: str
    blocks: list[Block]
    content_hash: str
    course: str | None = None
    section: str | None = None
    lecture: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks)


@dataclass
class ChunkDraft:
    ordinal: int
    heading: str
    text: str  # `title › heading` prefix + body (what is stored and embedded)
    body: str = ""  # without the prefix (what the dedupe hash is computed from)
    skill_slugs: list[str] = field(default_factory=list)
    t_start: float | None = None
    t_end: float | None = None
    kind: BlockKind = "prose"


class RuntimeCallFailed(RuntimeError):
    """A registry model call (STT, vision) failed. Carries what `model_call` needs so the failure
    is logged with `ok=False` instead of vanishing into a skip reason."""

    def __init__(
        self,
        *,
        task: str,
        provider: str,
        registry_id: str,
        model: str,
        error: str,
        latency_ms: int = 0,
    ) -> None:
        super().__init__(f"{task} call to {registry_id} failed: {error}")
        self.task, self.provider = task, provider
        self.registry_id, self.model = registry_id, model
        self.error, self.latency_ms = error, latency_ms


def content_hash(raw: bytes | str) -> str:
    data = raw.encode() if isinstance(raw, str) else raw
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Any) -> str:
    """Streamed sha256 of a file (large media never fully in memory)."""
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()
