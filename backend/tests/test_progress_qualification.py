import pytest

from app.kernel.progress_qualification import all_criteria_passed


@pytest.mark.parametrize(
    "results",
    [
        [],
        [{"criterion": "Explain", "passed": True}],
        [{"criterion": "Explain", "passed": True, "evidence": " "}],
        [{"criterion": "Explain", "passed": 1, "evidence": "answer"}],
        [{"criterion": "Different", "passed": True, "evidence": "answer"}],
        [{"criterion": "Explain", "passed": False, "evidence": "answer"}],
        [{"criterion": "Explain", "passed": True, "evidence": "answer"}] * 2,
    ],
)
def test_reject_incomplete_or_unverified_checks(results):
    assert not all_criteria_passed([{"criterion": "Explain"}], results)


def test_complete_exact_rubric_accepts_order_and_case_variation():
    criteria = [{"criterion": "Explain"}, {"criterion": "Apply"}]
    results = [
        {"criterion": "apply", "passed": True, "evidence": "worked example"},
        {"criterion": "EXPLAIN", "passed": True, "evidence": "causal explanation"},
    ]
    assert all_criteria_passed(criteria, results)
    assert not all_criteria_passed([], results)
    assert not all_criteria_passed(criteria + [criteria[0]], results)


@pytest.mark.parametrize(
    "facet,passed,label",
    [
        ("explanation", True, "Explanation check passed"),
        ("explanation", False, None),
        ("application", False, "Application attempted"),
        ("application", True, "Application check passed"),
    ],
)
async def test_reviewed_labels_preserve_history_and_disclose_revocation(
    db, learner, facet, passed, label
):
    from app.db.models import AssessmentAttempt
    from app.kernel import task_reviews
    from app.kernel.progress_qualification import reviewed_result
    from app.orchestrator import assessment_content
    from app.schemas.assessment_provenance import AssessmentProvenance
    from tests.test_task_reviews import command, setup_task

    task, _, _ = await setup_task(db)
    await task_reviews.decide(
        db, learner.id, task.id, await command(db, learner.id, task.id, facet=facet)
    )
    await db.commit()
    content = await task_reviews.snapshot(db, learner.id, task.id)
    binding = await task_reviews.capture(db, learner.id, task.id, content)
    digest = assessment_content.recovery_fingerprint(
        await assessment_content.snapshot(db, task.id, learner.id)
    )
    attempt = AssessmentAttempt(
        learner_id=learner.id,
        assessment_id=task.id,
        answer="Reasoned answer",
        grader_route="local",
        hint_count=0,
        content_fingerprint=digest,
    )
    attempt.llm_result_json = {
        "criterion_results": [
            {
                "criterion": "Give a causal explanation",
                "passed": passed,
                "evidence": "Reasoned answer",
            }
        ],
        "task_review_binding": binding.model_dump(),
        "evidence_provenance": AssessmentProvenance(
            task_kind="explain_back",
            content_fingerprint=digest,
            rubric_version=1,
            grading_method="local",
            reported_hint_count=0,
            revision_of_attempt_id=None,
        ).model_dump(),
    }
    db.add(attempt)
    await db.commit()
    result = await reviewed_result(db, learner.id, attempt)
    assert (result.label if result else None) == label
    if result:
        assert result.currently_eligible and result.independence == "not_verified"
    assert await reviewed_result(db, "foreign", attempt) is None
    original_payload = attempt.llm_result_json
    attempt.content_fingerprint = "different-content"
    attempt.llm_result_json = {
        **original_payload,
        "evidence_provenance": {
            **original_payload["evidence_provenance"],
            "content_fingerprint": "different-content",
        },
    }
    assert await reviewed_result(db, learner.id, attempt) is None
    attempt.content_fingerprint = digest
    attempt.llm_result_json = original_payload

    await task_reviews.decide(
        db,
        learner.id,
        task.id,
        await command(db, learner.id, task.id, facet=facet, decision="revoke", expected_revision=1),
    )
    await db.commit()
    historical = await reviewed_result(db, learner.id, attempt)
    if label:
        assert historical.label == label
        assert not historical.currently_eligible and historical.exclusion_reason
    task.item_json = {"prompt": "A different question"}
    await db.commit()
    await task_reviews.decide(
        db,
        learner.id,
        task.id,
        await command(db, learner.id, task.id, facet=facet, expected_revision=2),
    )
    await db.commit()
    after_reapproval = await reviewed_result(db, learner.id, attempt)
    if label:
        assert after_reapproval.label == label
        assert not after_reapproval.currently_eligible
    attempt.llm_result_json = {**attempt.llm_result_json, "evidence_provenance": {}}
    assert await reviewed_result(db, learner.id, attempt) is None
