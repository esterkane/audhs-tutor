"""Read-only impact preview; no publication authorization or learning writes."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_versions import token
from app.db.models import Assessment, Chunk, ReviewItem
from app.kernel import correction_drafts, question_state
from app.schemas.correction_drafts import CorrectionImpact, CorrectionPassage, CorrectionReview


async def preview(db: AsyncSession, learner_id: str, draft_id: str) -> CorrectionImpact:
    draft = await correction_drafts.get(db, learner_id, draft_id)
    current = await correction_drafts.original(db, draft.assessment_id, learner_id)
    state = await question_state.read(db, learner_id, draft.assessment_id)
    review = correction_drafts.review_snapshot(draft, current, state)
    reviews = list(
        await db.scalars(
            select(ReviewItem.id)
            .where(
                ReviewItem.learner_id == learner_id,
                ReviewItem.active.is_(True),
                question_state.review_reference() == draft.assessment_id,
                func.coalesce(ReviewItem.prompt_json["type"].as_string(), "") != "vocab",
            )
            .order_by(ReviewItem.id)
        )
    )
    exercises = list(
        await db.scalars(
            select(Assessment.id)
            .where(
                question_state.visible(learner_id),
                Assessment.kind == "code",
                Assessment.item_json["check_assessment_id"].as_string() == draft.assessment_id,
            )
            .order_by(Assessment.id)
        )
    )
    passages = []
    for source in current["source_evidence"]["items"]:
        chunk = await db.get(Chunk, source["reference"], populate_existing=True)
        text = chunk.text if chunk is not None else None
        passages.append(
            CorrectionPassage(
                reference=source["reference"],
                status=source["status"],
                text=text[:6000] if text is not None else None,
                truncated=text is not None and len(text) > 6000,
                document_version_id=source.get("document_version_id"),
            )
        )
    return CorrectionImpact(
        draft_id=draft.id,
        revision=draft.revision,
        preview_token=token(
            {
                "draft_id": draft.id,
                "revision": draft.revision,
                "candidate": draft.candidate_json,
                "rationale": draft.rationale,
                "original": current,
                "review": review,
                "question_state": state.model_dump(),
                "passages": [passage.model_dump() for passage in passages],
                "reviews": reviews,
                "exercises": exercises,
            }
        ),
        affected_reviews=len(reviews),
        linked_exercises=len(exercises),
        passages=passages,
        review=CorrectionReview.model_validate(review),
    )
