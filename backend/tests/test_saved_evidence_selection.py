import pytest

from app.integrations.supabase_evidence import stored_experiments
from app.orchestrator.saved_evidence_frame import supported_fact_frame
from app.orchestrator.saved_evidence_selection import source_choices
from tests.test_supabase_evidence import observation, recorded


def sources():
    return stored_experiments(
        recorded(observation())
        + recorded(observation(3, 1, "b"), "call-2")
        + recorded(observation(minimum=0, first="b"), "call-3")
    )


@pytest.mark.parametrize(
    "question,ordinals",
    [
        (
            (
                "Compare retry decisions in the first local experiment with the minimum-zero "
                "case. Use stored observations."
            ),
            [1, 3],
        ),
        (
            (
                "Vergleiche die Retry-Ergebnisse im ersten lokalen Versuch mit dem "
                "Minimum-null-Fall. Nutze gespeicherte Beobachtungen."
            ),
            [1, 3],
        ),
        (
            "Using saved experiments, compare retries for two active workers, minimum one, and minimum zero.",
            [1, 3],
        ),
        (
            "Using saved experiments, compare retries in the second experiment and the third experiment.",
            [2, 3],
        ),
    ],
)
def test_literal_qualifiers_identify_owned_sources_without_a_model(question, ordinals):
    records = sources()
    selected = source_choices(question, records, last_ordinal=3)
    assert selected is not None
    lookup = {r.source.id: r.ordinal for r in records}
    assert [lookup[identity] for identity in selected] == ordinals


@pytest.mark.parametrize(
    "quote",
    [
        "minimum one",
        "first local experiment, minimum zero",
        "minimum 1.5",
        "minimum -1",
        "unknown reference",
    ],
)
def test_ambiguous_or_conflicting_references_cannot_be_guessed(quote):
    question = "Compare retries from saved experiments: " + quote
    assert source_choices(question, sources(), last_ordinal=3) is None


@pytest.mark.parametrize(
    "topic",
    [
        "RLS",
        "authorization",
        "JWT",
        "production",
        "prices",
        "Kubernetes",
        "Qdrant",
        "mechanism",
        "SQLSTATE",
        "dependency cycles",
        "migration",
        "credentials",
        "learner mastery",
    ],
)
def test_unknown_substantive_requests_retain_the_complete_ordinary_tutor_path(topic):
    question = "Compare retries in the first saved experiment and discuss " + topic
    assert not supported_fact_frame(question)


def test_unknown_record_ids_and_failed_latest_trial_are_not_replaced_with_other_records():
    records = sources()
    assert (
        source_choices(
            "Compare retry results from saved experiment99-0123456789ab", records, last_ordinal=3
        )
        is None
    )
    history = recorded(observation()) + recorded(observation(minimum=0), "call-2")
    history[-1]["content"][0]["is_error"] = True
    assert (
        source_choices(
            "Compare retries in the last experiment from saved experiments",
            stored_experiments(history),
            last_ordinal=2,
        )
        is None
    )


@pytest.mark.parametrize(
    "question",
    [
        "Do not compare retries in the first saved experiment.",
        "No retry comparison in the first saved experiment.",
        "Compare the first saved retry experiment and update the workers.",
        "Only show the first saved retry count.",
    ],
)
def test_negative_or_extra_action_instructions_are_not_silently_ignored(question):
    assert not supported_fact_frame(question)


def test_record_ids_do_not_override_conflicting_requested_attributes():
    records = sources()
    identity = records[0].source.id
    assert (
        source_choices(
            f"Compare saved retry results for {identity} minimum zero", records, last_ordinal=3
        )
        is None
    )


def test_an_unresolved_additional_worker_reference_cannot_be_dropped():
    assert (
        source_choices(
            "Compare saved retries in the first experiment and twenty workers",
            sources(),
            last_ordinal=3,
        )
        is None
    )


@pytest.mark.parametrize(
    "extra",
    [
        "No fresh counts.",
        "No original decisions.",
        "Without final results.",
        "Keine neuen Ergebnisse.",
        "What if the first commit failed?",
        "Which actor committed first?",
    ],
)
def test_presentation_omissions_and_additional_semantics_are_not_treated_as_a_complete_report(
    extra,
):
    assert not supported_fact_frame(
        "Compare retry results from the first saved experiment. " + extra
    )
