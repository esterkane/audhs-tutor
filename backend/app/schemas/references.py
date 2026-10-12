"""Local copies of curated external pages; never a verification or reuse-rights grant."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReferenceLoad(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh: bool = False


class ReferenceImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: str = Field(pattern=r"^[a-f0-9]{64}$")


class ReferenceSnapshot(BaseModel):
    reference_id: str
    snapshot_id: str
    url: str
    title: str
    fetched_at: str
    license_url: str
    origin: Literal["third_party"] = "third_party"
    extraction_version: Literal["html-blocks.v1"] = "html-blocks.v1"
    text_preview: str
    extracted_characters: int
    note: str = "Local reading copy, not fact-checked. Images, interactive content and linked pages are not downloaded."


class ReferenceStatus(BaseModel):
    snapshot: ReferenceSnapshot | None = None


class ReferenceImported(BaseModel):
    document_id: str
    chunks: int
    indexed: int
    changed: bool
    note: str = "Added to the local library as third-party material. Search and choose relevant passages before asking."
