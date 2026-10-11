"""Dated learner evidence, without refreshing or modifying competency state."""

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AssessmentAttempt, CompetencyEvidence, TutorAnswer
from app.schemas.progress import ProgressDimension, ProgressEvidence, ProgressEvidencePage


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
        .outerjoin(
            AssessmentAttempt,
            and_(
                AssessmentAttempt.id == CompetencyEvidence.source_attempt_id,
                AssessmentAttempt.learner_id == learner_id,
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
