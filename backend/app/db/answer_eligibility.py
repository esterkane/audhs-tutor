"""One owner-scoped exclusion policy for saved-answer suggestions, retrieval and indexing.

History remains readable. Learner reports and detected format/provenance failures
exclude reuse; none of these filters certifies factual correctness.
"""

from sqlalchemy import CompoundSelect, func, select

from app.db.models import TutorAnswer, TutorAnswerFeedback, TutorAnswerReplacement


def excluded_answer_ids(learner_id: str) -> CompoundSelect[tuple[str]]:
    flags = func.json_each(TutorAnswer.metadata_json["flagged"]).table_valued("value")
    unsupported = (
        select(1)
        .select_from(flags)
        .where(flags.c.value.in_(["unsupported_numeric_citation", "socratic_format_mismatch"]))
        .correlate(TutorAnswer)
        .exists()
    )
    unchecked_socratic = (
        (TutorAnswer.metadata_json["questioning_style"].as_string() == "socratic")
        & (TutorAnswer.metadata_json["teaching_action"].as_string() == "explain")
        & (
            func.coalesce(
                TutorAnswer.metadata_json["socratic_format_checked"].as_boolean(), False
            ).is_(False)
        )
    )
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
                TutorAnswer.learner_id == learner_id,
                (TutorAnswer.surface == "assessment") | unsupported | unchecked_socratic,
            ),
        )
    )
