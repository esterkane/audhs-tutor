"""Bounded read-only correction discovery. Reports are not learning evidence."""

from typing import Any, Literal

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Assessment, CurriculumDraft, QuestionCorrectionDraft, QuestionFeedback
from app.schemas.question_corrections import CorrectionInbox, CorrectionReport


def wording(snapshot: dict[str, Any]) -> str:
    item = snapshot.get("item", snapshot)
    if not isinstance(item, dict):
        return "Question wording unavailable"
    for field in ("question", "prompt", "text"):
        if isinstance(item.get(field), str) and item[field].strip():
            return str(item[field])[:4000]
    return "Question wording unavailable"


async def inbox(db: AsyncSession, learner_id: str, offset: int, limit: int) -> CorrectionInbox:
    # Rank only non-withdrawn reports, consistently with the existing preference summary.
    # Filter verdict AFTER ranking so a newer good rating supersedes an earlier bad one.
    ranked = (
        select(
            QuestionFeedback.id,
            func.row_number()
            .over(
                partition_by=QuestionFeedback.target_key,
                order_by=(QuestionFeedback.created_at.desc(), QuestionFeedback.id.desc()),
            )
            .label("position"),
        )
        .where(
            QuestionFeedback.learner_id == learner_id,
            QuestionFeedback.withdrawn_at.is_(None),
        )
        .subquery()
    )
    query = (
        select(QuestionFeedback)
        .join(ranked, ranked.c.id == QuestionFeedback.id)
        .where(
            ranked.c.position == 1,
            QuestionFeedback.verdict == "bad",
            # Publication resolves precisely its attached report, after ranking so an
            # older report never reappears. The immutable report itself is retained.
            ~exists().where(
                QuestionCorrectionDraft.learner_id == learner_id,
                QuestionCorrectionDraft.feedback_id == QuestionFeedback.id,
                QuestionCorrectionDraft.status == "published",
            ),
        )
    )
    total = int(await db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = (
        await db.scalars(
            query.order_by(QuestionFeedback.created_at.desc(), QuestionFeedback.id.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    items = []
    for row in rows:
        current: dict[str, Any] | None = None
        status: Literal["unchanged", "changed", "unavailable"] = "unavailable"
        if row.assessment_id:
            assessment = await db.get(Assessment, row.assessment_id)
            if assessment is not None and assessment.owner_learner_id in (None, learner_id):
                current = {
                    "kind": assessment.kind,
                    "item": assessment.item_json,
                    "skill_id": assessment.skill_id,
                }
                status = "unchanged" if current == row.snapshot_json else "changed"
        elif row.draft_id:
            draft = await db.get(CurriculumDraft, row.draft_id)
            if draft is not None and draft.learner_id == learner_id:
                # Legacy feedback does not store an index. Never guess a new question
                # by position/title when a draft has changed.
                candidates = draft.payload_json.get("assessments", [])
                if draft.version == row.draft_version and row.snapshot_json in candidates:
                    current = row.snapshot_json
                    status = "unchanged"
                else:
                    status = "changed"
        items.append(
            CorrectionReport(
                id=row.id,
                target="assessment" if row.assessment_id else "draft",
                assessment_id=row.assessment_id,
                draft_id=row.draft_id,
                reported_question=wording(row.snapshot_json),
                current_question=wording(current) if current is not None else None,
                content_status=status,
                labels=[str(label) for label in row.labels_json],
                note=row.note,
                created_at=row.created_at,
            )
        )
    return CorrectionInbox(items=items, total=total, offset=offset, limit=limit)
