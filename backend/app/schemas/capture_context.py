"""Original browsing identity, never an arbitrary URL or a learning checkpoint."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Identity = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]


class ContextBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    label: str = Field(min_length=1, max_length=200)


class AreaCapture(ContextBase):
    kind: Literal["area"]
    area_id: Identity


class ProjectCapture(ContextBase):
    kind: Literal["project"]
    course_id: Identity
    section_id: Identity
    view: Literal["guide", "notebook"]


class AnswerCapture(ContextBase):
    kind: Literal["answer"]
    answer_id: Identity


class WorkspaceCapture(ContextBase):
    kind: Literal["workspace"]
    workspace_id: Identity


CaptureContext = Annotated[
    AreaCapture | ProjectCapture | AnswerCapture | WorkspaceCapture, Field(discriminator="kind")
]
