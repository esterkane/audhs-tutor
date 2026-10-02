"""One owner-scoped exclusion policy for saved-answer suggestions, retrieval and indexing.

History remains readable. These reports are learner preferences, not correctness evidence.
"""

from sqlalchemy import Select, select

from app.db.models import TutorAnswerFeedback


def excluded_answer_ids(learner_id: str) -> Select[tuple[str]]:
    return select(TutorAnswerFeedback.answer_id).where(
        TutorAnswerFeedback.learner_id == learner_id,
        TutorAnswerFeedback.hidden.is_(True)
        | TutorAnswerFeedback.verdict.in_(["incorrect", "outdated"]),
    )
