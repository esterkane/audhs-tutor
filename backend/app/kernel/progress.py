"""Dated learner evidence, without refreshing or modifying competency state."""

from pydantic import ValidationError
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Assessment, AssessmentAttempt, CompetencyEvidence, TutorAnswer
from app.schemas.assessment_provenance import AssessmentProvenance
from app.schemas.progress import (
    ProgressDimension,
    ProgressEvidence,
    ProgressEvidencePage,
    ProgressTaskContext,
)


def task_context(attempt: AssessmentAttempt | None) -> ProgressTaskContext | None:
    if attempt is None:
        return None
    snapshots = [
        result["evidence_provenance"]
        for result in (attempt.deterministic_result_json, attempt.llm_result_json)
        if isinstance(result, dict) and "evidence_provenance" in result
    ]
    # Missing fields must not acquire defaults that imply observed historical facts.
    if len(snapshots) != 1 or not isinstance(snapshots[0], dict):
        return None
    if not AssessmentProvenance.model_fields.keys() <= snapshots[0].keys():
        return None
    try:
        provenance = AssessmentProvenance.model_validate(snapshots[0], strict=True)
    except ValidationError:
        return None
    if (
        provenance.content_fingerprint != attempt.content_fingerprint
        or provenance.grading_method != attempt.grader_route
        or provenance.reported_hint_count != attempt.hint_count
        or provenance.revision_of_attempt_id != attempt.revision_of_attempt_id
        or not provenance.task_kind.strip()
        or not provenance.grading_method.strip()
    ):
        return None
    return ProgressTaskContext(
        task_kind=provenance.task_kind,
        rubric_version=provenance.rubric_version,
        grading_method=provenance.grading_method,
        reported_hint_count=provenance.reported_hint_count,
        revised_work=provenance.revision_of_attempt_id is not None,
    )


async def evidence_page(
    db: AsyncSession, learner_id: str, skill_id: str, *, offset: int, limit: int
) -> ProgressEvidencePage:
    scope = (
        CompetencyEvidence.learner_id == learner_id,
        CompetencyEvidence.skill_id == skill_id,
    )
    total = await db.scalar(select(func.count()).select_from(CompetencyEvidence).where(*scope))
    dimensions = await db.execute(
        select(CompetencyEvidence.dimension, func.count(), func.max(CompetencyEvidence.ts))
        .where(*scope)
        .group_by(CompetencyEvidence.dimension)
        .order_by(CompetencyEvidence.dimension)
    )
    rows = await db.execute(
        select(CompetencyEvidence, AssessmentAttempt, TutorAnswer.id)
        .select_from(CompetencyEvidence)
        .outerjoin(
            AssessmentAttempt,
            and_(
                AssessmentAttempt.id == CompetencyEvidence.source_attempt_id,
                AssessmentAttempt.learner_id == learner_id,
                AssessmentAttempt.assessment_id.in_(
                    select(Assessment.id).where(Assessment.skill_id == skill_id)
                ),
            ),
        )
        .outerjoin(
            TutorAnswer,
            and_(
                TutorAnswer.turn_id == "assessment:" + AssessmentAttempt.id,
                TutorAnswer.learner_id == learner_id,
                TutorAnswer.surface == "assessment",
            ),
        )
        .where(*scope)
        .order_by(CompetencyEvidence.ts.desc(), CompetencyEvidence.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return ProgressEvidencePage(
        skill_id=skill_id,
        total=total or 0,
        offset=offset,
        limit=limit,
        dimensions=[
            ProgressDimension(dimension=dimension, count=count, last_recorded_at=ts)
            for dimension, count, ts in dimensions
        ],
        items=[
            ProgressEvidence(
                task_context=task_context(attempt),
                id=evidence.id,
                answer_id=answer_id,
                dimension=evidence.dimension,
                recorded_at=evidence.ts,
                score=evidence.score,
                weight=evidence.weight,
                grader_level=evidence.grader_level,
                attempt_id=attempt.id if attempt else None,
                reported_hint_count=attempt.hint_count if attempt else None,
            )
            for evidence, attempt, answer_id in rows
        ],
    )
