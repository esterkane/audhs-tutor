from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update

from app.api.deps import DB, Learner
from app.core.errors import AppError
from app.db.models import LearningProject
from app.kernel.projects import ensure_projects

router = APIRouter(prefix="/projects", tags=["projects"])


class LearningProjectOut(BaseModel):
    id: str
    slug: str
    title: str
    topic: str
    objective: str
    brief: dict[str, Any]
    notes: str
    evidence: str
    reflection: str
    status: str
    version: int


def output(row: LearningProject) -> LearningProjectOut:
    return LearningProjectOut(
        id=row.id,
        slug=row.slug,
        title=row.title,
        topic=row.topic,
        objective=row.objective,
        brief=row.brief_json,
        notes=row.notes,
        evidence=row.evidence,
        reflection=row.reflection,
        status=row.status,
        version=row.version,
    )


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    notes: str = Field(max_length=16000)
    evidence: str = Field(max_length=24000)
    reflection: str = Field(max_length=16000)
    status: Literal["planned", "working", "submitted"]


@router.get("", response_model=list[LearningProjectOut])
async def listing(db: DB, learner: Learner) -> list[LearningProjectOut]:
    return [output(row) for row in await ensure_projects(db, learner.id)]


@router.put("/{project_id}", response_model=LearningProjectOut)
async def save(
    project_id: str, body: ProjectUpdate, db: DB, learner: Learner
) -> LearningProjectOut:
    learner_id = learner.id
    if body.status == "submitted" and (not body.evidence.strip() or not body.reflection.strip()):
        raise AppError(
            "project_evidence_needed",
            "Record test evidence and your reflection before submitting.",
            422,
        )
    changed = await db.scalar(
        update(LearningProject)
        .where(
            LearningProject.id == project_id,
            LearningProject.learner_id == learner_id,
            LearningProject.version == body.expected_version,
        )
        .values(
            notes=body.notes,
            evidence=body.evidence,
            reflection=body.reflection,
            status=body.status,
            version=LearningProject.version + 1,
        )
        .returning(LearningProject.id)
    )
    if changed is None:
        await db.rollback()
        prior = await db.scalar(
            select(LearningProject)
            .where(LearningProject.id == project_id, LearningProject.learner_id == learner_id)
            .execution_options(populate_existing=True)
        )
        if (
            prior is not None
            and prior.version == body.expected_version + 1
            and all(
                getattr(prior, key) == getattr(body, key)
                for key in ["notes", "evidence", "reflection", "status"]
            )
        ):
            return output(prior)
        raise AppError(
            "project_changed",
            "This project changed or is unavailable. Reload; your local writing is kept.",
            409,
        )
    await db.commit()
    row = await db.scalar(
        select(LearningProject)
        .where(LearningProject.id == project_id, LearningProject.learner_id == learner_id)
        .execution_options(populate_existing=True)
    )
    assert row is not None
    return output(row)
