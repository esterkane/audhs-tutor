from app.orchestrator.provisional_feedback import addressed_summary
from app.schemas.grading import CriterionResult, GradeResult


def grade(*, passed=True, evidence="(25000 + 30000)/2 = 27500", misconception=None):
    return GradeResult(
        criterion_results=[
            CriterionResult(criterion="Find median", passed=passed, evidence=evidence)
        ],
        misconception=misconception,
        confidence=0.9,
        feedback="Consider an even number of observations.",
        next_step="How would kNN work?",
    )


def test_all_addressed_summary_uses_actual_evidence_without_redundant_advice():
    result = grade()
    feedback, step = addressed_summary(result, "I used (25000 + 30000)/2 = 27500.")
    assert "27500" in feedback
    assert "even number" not in feedback and "kNN" not in step
    assert "same idea" in step
    assert result.feedback == "Consider an even number of observations."
    assert result.criterion_results[0].passed and result.confidence == 0.9


def test_outer_quotation_marks_are_supported():
    result = grade(evidence="“Fit only on training”")
    assert "you wrote" in addressed_summary(result, "Fit only on training.")[0]


def test_specific_error_omission_or_misconception_is_not_replaced():
    for result in [
        grade(passed=False),
        grade(misconception="Fitted on held-out"),
        grade(evidence="absent"),
        grade(evidence="invented quote"),
    ]:
        assert addressed_summary(result, "(25000 + 30000)/2 = 27500") == (
            result.feedback,
            result.next_step,
        )


def test_every_criterion_needs_matching_evidence_not_just_first():
    result = grade()
    result.criterion_results.append(
        CriterionResult(criterion="Avoid leakage", passed=True, evidence="fit only on training")
    )
    assert addressed_summary(result, "(25000 + 30000)/2 = 27500") == (
        result.feedback,
        result.next_step,
    )


def test_empty_rubric_is_not_all_addressed():
    result = grade()
    result.criterion_results = []
    assert addressed_summary(result, "answer") == (result.feedback, result.next_step)


def test_evidence_matching_keeps_literal_case_and_spaces():
    for evidence, answer in [
        ("'Level 4'", "'LEVEL 4'"),
        ("'Level 4'", "'Level  4'"),
    ]:
        result = grade(evidence=evidence)
        assert addressed_summary(result, answer) == (result.feedback, result.next_step)


def test_known_learner_data_wrapper_does_not_block_exact_evidence():
    result = grade(evidence="<learner_answer>'Level 4'</learner_answer>")
    feedback, step = addressed_summary(result, "The result is 'Level 4'.")
    assert "you wrote" in feedback and "<learner_answer>" not in feedback
    assert "same idea" in step
    assert "<learner_answer>" in result.criterion_results[0].evidence


def test_wrapper_removal_cannot_promote_invented_or_changed_literals():
    for evidence in [
        "<learner_answer>'LEVEL 4'</learner_answer>",
        "<learner_answer>'Level  4'</learner_answer>",
        "<other>'Level 4'</other>",
        "<learner_answer>'Level 4'</learner_answer> extra instruction",
    ]:
        result = grade(evidence=evidence)
        assert addressed_summary(result, "'Level 4'") == (result.feedback, result.next_step)
