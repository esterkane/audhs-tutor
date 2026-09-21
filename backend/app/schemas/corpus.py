"""Corpus (knowledge system) API schemas: stats, documents, ingest, search inspection."""

from typing import Any

from pydantic import BaseModel, Field


class CourseStats(BaseModel):
    course: str
    documents: int
    chunks: int
    flagged: int
    source_types: list[str]
    trust_tiers: list[int]


class IndexStateOut(BaseModel):
    collection: str
    embedding_registry_id: str
    embedding_version: int
    dims: int
    chunk_count: int
    last_reindex: str | None


class RetrievalConfigOut(BaseModel):
    collection: str
    reranker: str | None = Field(default=None, description="registry model used after fusion")
    max_per_document: int


class CorpusStats(BaseModel):
    retrieval: RetrievalConfigOut
    documents: int
    versions: int
    chunks: int
    flagged_chunks: int
    courses: list[CourseStats]
    index: IndexStateOut | None
    index_count: int | None = Field(default=None, description="live count from the retrieval index")


class DocumentOut(BaseModel):
    id: str
    title: str
    source_type: str
    uri: str
    course: str | None
    section: str | None
    lecture: str | None
    version: int
    chunks: int
    flagged: int
    trust_tier: int
    ingested_at: str | None


class DocumentList(BaseModel):
    documents: list[DocumentOut]


class RetierRequest(BaseModel):
    trust_tier: int = Field(ge=0, le=3)


class IngestRequest(BaseModel):
    path: str = Field(description="local file or folder (Udemy layout: Course/Section/Lecture)")
    course: str | None = None
    trust_tier: int = Field(default=2, ge=0, le=3)
    source_type: str | None = None
    index: bool = True
    language: str | None = Field(
        default=None,
        pattern=r"^[a-z]{2,3}$",
        description="force the transcription language (ISO 639 code); null = auto",
    )
    media: bool = Field(
        default=True, description="transcribe audio/video and read images (false: list as skipped)"
    )


class IngestDocResult(BaseModel):
    document_id: str
    title: str
    course: str | None
    source_type: str
    version: int
    chunks: int
    changed: bool
    deduped: int
    flagged: int
    indexed: int
    trust_updated: bool = False
    reverted: bool = False
    transcribed_seconds: float | None = None
    vision: bool = False


class ToolStatus(BaseModel):
    ready: bool
    registry_id: str | None = None
    detail: str
    package_installed: bool | None = None


class IngestCapabilities(BaseModel):
    formats: dict[str, list[str]]
    unsupported: dict[str, str]
    archives: list[str]
    audio: list[str]
    video: list[str]
    images: list[str]
    stt: ToolStatus
    vision: ToolStatus
    audio_decoder: str | None
    legacy_office: str | None
    image_converter: str | None


class SkippedFile(BaseModel):
    path: str
    reason: str


class IngestOut(BaseModel):
    summary: dict[str, Any]
    results: list[IngestDocResult]
    skipped: list[SkippedFile]


class ForgetOut(BaseModel):
    document_id: str
    chunks_removed: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=8, ge=1, le=50)
    course: str | None = None
    section: str | None = None
    lecture: str | None = None
    source_type: str | None = None
    skill_ids: list[str] | None = None
    min_trust_tier: int | None = Field(default=None, ge=0, le=3)
    tutor_view: bool = Field(
        default=False, description="apply the tutor's trust floor and mark quarantined hits"
    )


class SearchHit(BaseModel):
    chunk_id: str
    rank: int
    score: float
    dense_score: float | None
    sparse_score: float | None
    rerank_score: float | None = None
    citation: str
    course: str | None
    section: str | None
    lecture: str | None
    source_type: str
    trust_tier: int
    t_start: float | None
    flagged: list[str]
    quarantined: bool = False
    text: str


class SearchOut(BaseModel):
    query: str
    hits: list[SearchHit]
    latency_ms: int
    reranked: bool
    flagged_patterns: list[str]
    collection: str
