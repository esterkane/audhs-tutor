"""P4: course → curriculum drafts, material status, source passages, content reports."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MaterialStatus(BaseModel):
    course: str
    documents: int
    chunks: int
    drafts: int
    published_skills: int
    status: str  # imported | searchable | draft | published


class MaterialList(BaseModel):
    courses: list[MaterialStatus]


class SectionOut(BaseModel):
    section: str | None
    documents: int


class SectionList(BaseModel):
    course: str
    sections: list[SectionOut]


class DraftCreate(BaseModel):
    course: str = Field(min_length=1, max_length=200)
    section: str | None = Field(default=None, max_length=300)
    use_model: bool = Field(
        default=False,
        description="ask the routed local model to draft objectives/exercises (untrusted until reviewed)",
    )


class ProblemOut(BaseModel):
    level: str  # error | warning | info
    where: str
    message: str


class CourseSourceOut(BaseModel):
    document_id: str
    title: str
    section: str | None
    lecture: str | None
    source_type: str
    uri: str
    chunks: int
    role: str  # primary | supplemental | excluded
    reason: str
    decided_by: str  # owner | suggested


class CourseSourceList(BaseModel):
    course: str
    sources: list[CourseSourceOut]
    counts: dict[str, int]


class CourseSourceRoleIn(BaseModel):
    role: str = Field(pattern=r"^(primary|supplemental|excluded)$")
    reason: str = Field(default="", max_length=500)


class CourseSourceRoleOut(BaseModel):
    document_id: str
    role: str
    reason: str
    decided_by: str


class ArchiveRoleIn(CourseSourceRoleIn):
    archive: str = Field(min_length=1, max_length=500, description="archive file name or uri")


class ArchiveRoleOut(BaseModel):
    archive: str
    role: str
    documents: int


class DraftOut(BaseModel):
    id: str
    area_id: str | None = None
    course: str | None
    section: str | None
    title: str
    status: str
    origin: str
    version: int
    payload: dict[str, Any]
    problems: list[ProblemOut]
    created_at: str
    updated_at: str
    published_at: str | None
    model_call_id: str | None = None


class DraftList(BaseModel):
    drafts: list[DraftOut]


class SkillIn(BaseModel):
    """Shape check for hand-edited JSON (the kernel validates meaning). Unknown keys are kept."""

    model_config = ConfigDict(extra="allow")
    slug: str = Field(max_length=120)
    title: str = Field(max_length=300)
    description: str = Field(default="", max_length=2000)
    prerequisites: list[str] = Field(default_factory=list, max_length=20)
    success_criteria: list[str] = Field(default_factory=list, max_length=12)
    assessment_requirements: dict[str, Any] = Field(default_factory=dict)
    example_applications: list[str] = Field(default_factory=list, max_length=12)


class LearningObjectIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    skill: str = Field(max_length=120)
    concept: str = Field(default="", max_length=300)
    goal: str = Field(default="", max_length=1000)
    examples: list[str] = Field(default_factory=list, max_length=8)
    exercises: list[str] = Field(default_factory=list, max_length=8)
    success_criteria: list[str] = Field(default_factory=list, max_length=12)
    sources: list[str] = Field(default_factory=list, max_length=64)


class AssessmentIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    skill: str = Field(max_length=120)
    kind: str = Field(max_length=40)
    item: dict[str, Any] = Field(default_factory=dict)
    source_chunk_id: str | None = None
    rubric: list[Any] | dict[str, Any] | None = None
    auto: bool = False
    guessable: bool = False
    origin: str | None = None


class DraftPayload(BaseModel):
    """A whole draft as the learner may edit it. Sizes are capped; the kernel's `validate_payload`
    adds the semantic problems (unknown prerequisites, cycles, missing assessments, …)."""

    model_config = ConfigDict(extra="allow")
    domain: str = Field(default="ai_ml", max_length=40)
    course: str | None = Field(default=None, max_length=200)
    section: str | None = Field(default=None, max_length=300)
    skills: list[SkillIn] = Field(default_factory=list, max_length=60)
    learning_objects: list[LearningObjectIn] = Field(default_factory=list, max_length=60)
    assessments: list[AssessmentIn] = Field(default_factory=list, max_length=300)
    selection: dict[str, Any] | None = Field(
        default=None, description="what the draft was built on (kept across edits; kernel-written)"
    )


class DraftUpdate(BaseModel):
    payload: DraftPayload


class PublishOut(BaseModel):
    draft: DraftOut
    skills: int
    edges: int
    learning_objects: int
    new_object_versions: int
    assessments: int


class ChunkOut(BaseModel):
    """One source passage for the citation viewer. `open_url` is the http(s) URI as-is, or the
    app's guarded file endpoint (`/api/curriculum/chunks/{id}/file#t=…`) when the document is a
    plain file under INGEST_ROOTS; otherwise None and the path is shown."""

    chunk_id: str
    text: str
    citation: str
    course: str | None
    section: str | None
    lecture: str | None
    source_type: str
    trust_tier: int
    document_title: str
    uri: str
    open_url: str | None
    t_start: float | None
    t_end: float | None
    prev_text: str | None
    next_text: str | None


class ReportIn(BaseModel):
    kind: str = Field(pattern="^(wrong_source|wrong_explanation|wrong_grading|wrong_item|other)$")
    turn_id: str | None = None
    chunk_id: str | None = None
    skill_id: str | None = None
    assessment_id: str | None = None
    note: str = Field(default="", max_length=2000)


class ReportOut(BaseModel):
    id: str
    kind: str
    turn_id: str | None
    chunk_id: str | None
    skill_id: str | None
    assessment_id: str | None = None
    note: str
    status: str
    created_at: str


class ReportList(BaseModel):
    reports: list[ReportOut]
