"""One owner-scoped exclusion policy for saved-answer suggestions, retrieval and indexing.

History remains readable. These reports are learner preferences, not correctness evidence.
"""

from sqlalchemy import CompoundSelect, select

from app.db.models import TutorAnswer, TutorAnswerFeedback, TutorAnswerReplacement


def excluded_answer_ids(learner_id: str) -> CompoundSelect[tuple[str]]:
    return (
        select(TutorAnswerFeedback.answer_id)
        .where(
            TutorAnswerFeedback.learner_id == learner_id,
            TutorAnswerFeedback.hidden.is_(True)
            | TutorAnswerFeedback.verdict.in_(["incorrect", "outdated"]),
        )
        .union(
            select(TutorAnswerReplacement.answer_id).where(
                TutorAnswerReplacement.learner_id == learner_id,
                TutorAnswerReplacement.replacement_id.is_not(None),
            ),
            select(TutorAnswer.id).where(
                TutorAnswer.learner_id == learner_id, TutorAnswer.surface == "assessment"
            ),
        )
    )
