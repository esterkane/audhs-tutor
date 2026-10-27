"""Project evidence is saved safely and never confers mastery by itself."""

import pytest
from sqlalchemy import func, select

from app.api.projects import ProjectUpdate, save
from app.core.errors import AppError
from app.db.models import CompetencyEvidence, LearnerProfile, LearningProject
from app.kernel.projects import ensure_projects


def body(version=1, **changes):
    values = dict(
        expected_version=version,
        notes="My experiment",
        evidence="",
        reflection="",
        status="working",
    )
    values.update(changes)
    return ProjectUpdate(**values)


async def test_bootstrap_is_idempotent_and_owner_scoped(db, learner):
    first = await ensure_projects(db, learner.id)
    second = await ensure_projects(db, learner.id)
    assert len(first) == 6
    assert {x.id for x in first} == {x.id for x in second}
    other = LearnerProfile(display_name="Other learner")
    db.add(other)
    await db.commit()
    own = await ensure_projects(db, other.id)
    assert len(own) == 6
    assert not {x.id for x in first} & {x.id for x in own}


async def test_save_retry_and_stale_update_preserve_writing(db, learner):
    project = (await ensure_projects(db, learner.id))[0]
    project_id = project.id
    request = body()
    saved = await save(project_id, request, db, learner)
    assert saved.version == 2
    assert saved.notes == "My experiment"
    retry = await save(project_id, request, db, learner)
    assert retry.version == 2
    await db.refresh(learner)  # A new HTTP request resolves its learner afresh.
    with pytest.raises(AppError):
        await save(project_id, body(version=1, status="planned"), db, learner)
    await db.rollback()
    latest = await db.get(LearningProject, project_id)
    assert latest.notes == "My experiment"
    assert latest.version == 2


async def test_submission_requires_evidence_and_never_awards_mastery(db, learner):
    project = (await ensure_projects(db, learner.id))[0]
    project_id = project.id
    with pytest.raises(AppError):
        await save(
            project_id,
            ProjectUpdate(
                expected_version=1, notes="", evidence=" ", reflection="", status="submitted"
            ),
            db,
            learner,
        )
    saved = await save(
        project_id,
        ProjectUpdate(
            expected_version=1,
            notes="",
            evidence="Measured query plan",
            reflection="Explain the observed change",
            status="submitted",
        ),
        db,
        learner,
    )
    assert saved.status == "submitted"
    assert await db.scalar(select(func.count()).select_from(CompetencyEvidence)) == 0


async def test_other_owner_cannot_read_or_overwrite_project(db, learner):
    project = (await ensure_projects(db, learner.id))[0]
    project_id = project.id
    other = LearnerProfile(display_name="Other learner")
    db.add(other)
    await db.commit()
    with pytest.raises(AppError):
        await save(project_id, body(), db, other)
    await db.rollback()
    latest = await db.get(LearningProject, project_id)
    assert latest.version == 1 and latest.notes == ""
