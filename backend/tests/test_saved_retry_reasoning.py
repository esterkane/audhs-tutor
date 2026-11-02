import copy

import pytest

from app.integrations.supabase_reviewed import ReviewedOrchestrator
from app.orchestrator.saved_evidence import answer_saved_retry
from tests.test_supabase_evidence import observation, recorded
from tests.test_supabase_membership import state

QUESTION = (
    "Why did the full retry in the first experiment decide not to deactivate its row even "
    "though its commit succeeded? Use the recorded observations, and explain the distinction "
    "from UPDATE-only in that same experiment. Do not run new SQL."
)
GERMAN = (
    "Warum hat der vollständige Retry im ersten gespeicherten Versuch entschieden, "
    "die eigene Zeile nicht zu deaktivieren, obwohl sein Commit erfolgreich war? "
    "Erkläre den Unterschied zum UPDATE-only im gleichen Versuch. Keine neuen SQL-Befehle."
)


@pytest.mark.parametrize("language,question", [("en", QUESTION), ("de", GERMAN)])
@pytest.mark.parametrize(
    "workers,minimum,first", [(2, 1, "a"), (2, 0, "b"), (3, 1, "a"), (3, 2, "b"), (5, 3, "b")]
)
async def test_causal_reasoning_is_bound_to_actual_values_even_when_question_premise_is_false(
    language, question, workers, minimum, first
):
    history = recorded(observation(workers, minimum, first))
    before = copy.deepcopy(history)

    class NoModel:
        def __getattribute__(self, name):
            raise AssertionError("Verified causal arithmetic must not call a model")

    answer = await answer_saved_retry(question, state(language=language), history, NoModel())
    assert answer is not None
    assert answer.method == "literal-reference-causal-proof.v1"
    assert f"{workers - 1} > {minimum} = {str(workers - 1 > minimum).lower()}" in answer.text
    assert f"{workers} > {minimum} = true" in answer.text
    assert ("deshalb" if language == "de" else "so the decision was") in answer.text
    assert ("ursprüngliche Anzahl" if language == "de" else "reused original count") in answer.text
    assert (
        "Commit erfolgreich: ja" if language == "de" else "commit succeeded: yes"
    ) in answer.text
    assert "Repeatable Read" not in answer.text and "write-consistent" not in answer.text
    if workers - 1 > minimum:
        assert (
            "Entscheidung: eigene Zeile deaktivieren"
            if language == "de"
            else "decision was: deactivate own row"
        ) in answer.text
    assert history == before


@pytest.mark.parametrize(
    "tail",
    [
        " Also explain snapshot identity.",
        " Also diagnose RLS.",
        " And execute the fix.",
        " What if the minimum were different?",
        " Which transaction lost its changes?",
    ],
)
async def test_uncovered_causal_parts_preserve_full_tutor_path(tail):
    assert await answer_saved_retry(QUESTION + tail, state(), recorded(observation())) is None


@pytest.mark.parametrize(
    "changes",
    [{"mode": "exam"}, {"mode": "incident"}, {"delivery": "socratic"}, {"active_lab": object()}],
)
async def test_learning_and_lab_modes_are_not_bypassed(changes):
    assert await answer_saved_retry(QUESTION, state(**changes), recorded(observation())) is None


async def test_missing_retries_and_tampered_predicates_do_not_manufacture_a_cause():
    assert await answer_saved_retry(QUESTION, state(), recorded(observation(2, 2))) is None
    value = observation()
    value["runs"][3]["retry"]["decision"] = True
    assert await answer_saved_retry(QUESTION, state(), recorded(value)) is None


async def test_orchestrator_keeps_complete_original_question_history_and_empty_mastery():
    from backend.tutor.orchestrator import Final

    class Delegate:
        client = None

        async def run_turn(self, **kwargs):
            pytest.fail("No second model paraphrase")
            yield

    history = recorded(observation())
    before = copy.deepcopy(history)
    events = [
        event
        async for event in ReviewedOrchestrator(Delegate()).run_turn(
            history=history, user_text=QUESTION, state=state(active_lab=None), ctx=None
        )
    ]
    final = next(event for event in events if isinstance(event, Final))
    assert final.model == "local:saved-retry-reasoning.v1"
    assert final.turn.ledger_delta == [] and final.turn.next_question is None
    assert final.new_messages[0] == {"role": "user", "content": QUESTION}
    assert final.new_messages[-1]["content"] == final.turn.text
    assert history == before


async def test_general_motivation_question_is_not_mistaken_for_a_recorded_decision():
    assert (
        await answer_saved_retry(
            "Why compare full retry and UPDATE-only in the first saved experiment?",
            state(),
            recorded(observation()),
        )
        is None
    )


@pytest.mark.parametrize("minimum", ["0.5", "-0.5"])
async def test_removing_format_constraints_does_not_rewrite_fractional_references(minimum):
    question = QUESTION.replace("first experiment", f"first experiment (minimum {minimum})")
    assert await answer_saved_retry(question, state(), recorded(observation(minimum=0))) is None


@pytest.mark.parametrize(
    "constraint",
    [
        "Kein neues SQL ausführen.",
        "Keine neuen SQL-Befehle.",
        "Do not execute new SQL.",
        "No commands or invented observations.",
    ],
)
async def test_equivalent_constraints_keep_actual_german_retry_question_on_verified_path(
    constraint,
):
    question = (
        "Warum entschied der vollständige Retry im ersten Versuch, seine Zeile nicht zu "
        "deaktivieren, obwohl der Commit erfolgreich war? Nutze die gespeicherten Beobachtungen "
        "und erkläre den Unterschied zu UPDATE-only im selben Versuch. " + constraint
    )
    answer = await answer_saved_retry(question, state(language="de"), recorded(observation()))
    assert answer is not None and answer.method == "literal-reference-causal-proof.v1"
    assert "1 > 1 = false" in answer.text and "2 > 1 = true" in answer.text
    assert "deshalb lautete die Entscheidung" in answer.text


@pytest.mark.parametrize(
    "suffix",
    [" Execute new SQL.", " Run the experiment.", " No SQL and explain snapshot identity."],
)
async def test_recognizing_negative_execution_constraints_does_not_swallow_other_requests(suffix):
    assert await answer_saved_retry(QUESTION + suffix, state(), recorded(observation())) is None


async def test_do_not_invent_observations_is_not_confused_with_no_observations():
    assert (
        await answer_saved_retry(QUESTION + " No observations.", state(), recorded(observation()))
        is None
    )
