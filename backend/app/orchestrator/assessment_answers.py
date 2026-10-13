"""Save completed grading feedback as history, never regrade or write learning evidence."""

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.answer_recovery import AnswerRecovery
from app.db.answers import save_completed
from app.schemas.grading import AssessmentOutcome, AttemptRequest, AttemptResult
from app.schemas.provisional_feedback import ProvisionalFeedbackResult

logger = logging.getLogger(__name__)


def feedback_snapshot(
    result: AssessmentOutcome,
    request: AttemptRequest,
    *,
    learner_id: str,
    question: dict[str, Any],
    area_id: str | None,
    course_label: str | None,
) -> dict[str, Any]:
    provisional = isinstance(result, ProvisionalFeedbackResult)
    if isinstance(result, ProvisionalFeedbackResult):
        identity = result.feedback_id
        prefix = (
            "Model feedback — not an assessed result. Mastery and review schedule unchanged.\n\n"
        )
    else:
        identity = result.attempt_id
        prefix = (
            (
                "Repeated practice on a previously checked question. "
                "Learning evidence and review schedule unchanged.\n\n"
            )
            if result.revision_of_attempt_id
            else ""
        )
    answer_display = request.answer
    options = question.get("options")
    index = request.answer.strip()
    if question.get("kind") == "mcq" and isinstance(options, list) and index.isdigit():
        choice = int(index)
        if choice < len(options):
            answer_display = str(options[choice])
    snapshot: dict[str, Any] = dict(
        learner_id=learner_id,
        session_id=request.session_id,
        turn_id=f"provisional:{identity}" if provisional else f"assessment:{identity}",
        surface="assessment",
        request={
            "text": question["question"],
            "learner_answer": request.answer,
            "learner_answer_display": answer_display,
        },
        text=prefix + f"{result.feedback}\n\n{result.next_step}",
        metadata={
            **(
                {"provisional_feedback_id": identity}
                if provisional
                else {"assessment_attempt_id": identity}
            ),
            "assessment_id": result.assessment_id,
            "skill_id": result.skill_id,
            "area_id": area_id,
            "course_label": course_label,
            "assessment_question": question,
            "assessment_result": result.model_dump(
                exclude={"answer_id", "save_error", "save_receipt"}
            ),
            "sources": [],
            "provenance_available": False,
        },
    )
    return snapshot


async def save_feedback(
    db: AsyncSession,
    result: AttemptResult,
    request: AttemptRequest,
    *,
    learner_id: str,
    question: dict[str, Any],
    area_id: str | None,
    course_label: str | None,
    recovery: AnswerRecovery | None,
) -> AttemptResult:
    snapshot = feedback_snapshot(
        result,
        request,
        learner_id=learner_id,
        question=question,
        area_id=area_id,
        course_label=course_label,
    )
    if not snapshot["text"].strip():
        return result.model_copy(
            update={
                "save_error": "Grading finished without feedback text to save. Your grading result remains here."
            }
        )
    try:
        answer = await save_completed(db, **snapshot)
        return result.model_copy(update={"answer_id": answer.id})
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.warning("Assessment feedback save failed: %s", type(exc).__name__)
        return result.model_copy(
            update={
                "save_error": (
                    "Grading finished, but feedback could not be saved to answer history. "
                    "Retry saving, not grading."
                ),
                "save_receipt": recovery.issue(snapshot) if recovery else None,
            }
        )
