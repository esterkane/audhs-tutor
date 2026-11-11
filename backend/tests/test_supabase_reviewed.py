from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.integrations.supabase_reviewed import ReviewedOrchestrator, matches, reviewed_turn

QUESTION = (
    "Explain the difference between a missing SELECT grant and a row policy that matches no rows."
)


def state(**changes):
    return SimpleNamespace(
        **(
            dict(
                delivery="explicit",
                mode="lesson",
                language="en",
                persona_on=False,
                active_lab=None,
                incident=None,
            )
            | changes
        )
    )


@pytest.mark.parametrize(
    "text",
    [
        QUESTION,
        "Erkläre den Unterschied zwischen fehlender SELECT-Berechtigung und RLS ohne passende Zeilen: keine Zeilen.",
    ],
)
def test_exact_distinction_supported(text):
    assert matches(text, state())


@pytest.mark.parametrize(
    "text",
    [
        "Explain INSERT RLS errors",
        "Explain SELECT policies",
        QUESTION + " CREATE POLICY for me",
        "SELECT * FROM private_table",
        "Compare grant and no rows in a view policy SELECT",
        "```sql " + QUESTION,
    ],
)
def test_other_requests_decline(text):
    assert not matches(text, state())


@pytest.mark.parametrize(
    "changes",
    [
        dict(delivery="socratic"),
        dict(mode="exam"),
        dict(active_lab=object()),
        dict(incident=object()),
    ],
)
def test_preserves_learning_modes(changes):
    assert not matches(QUESTION, state(**changes))


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("persona_on", [False, True])
def test_reviewed_turn_has_no_mastery_or_execution_claims(language, persona_on):
    turn = reviewed_turn(state(language=language, persona_on=persona_on))
    assert turn.language == language and turn.persona_on == persona_on
    assert not turn.ledger_delta and turn.lab_action is None and turn.path is None
    assert "has_table_privilege(current_user, c.oid, 'SELECT')" in turn.text
    assert "policyname" in turn.text and "policy_id" not in turn.text
    assert "```" not in turn.speech
    assert "not been run" in turn.text if language == "en" else "nicht gegen deine" in turn.text


async def test_reuse_appends_full_turn_without_model_call():
    delegate = SimpleNamespace(run_turn=AsyncMock())
    before = [{"role": "user", "content": "Earlier private research"}]
    events = [
        event
        async for event in ReviewedOrchestrator(delegate).run_turn(
            history=before, user_text=QUESTION, state=state()
        )
    ]
    delegate.run_turn.assert_not_called()
    assert before == [{"role": "user", "content": "Earlier private research"}]
    final = events[-1]
    assert final.new_messages[0]["content"] == QUESTION
    assert final.new_messages[1]["content"] == final.turn.text
    assert final.model.startswith("reviewed:")


async def test_unrelated_request_delegates_unchanged():
    captured = {}

    async def run_turn(**kwargs):
        captured.update(kwargs)
        yield "original event"

    args = dict(
        history=[{"role": "user", "content": "Earlier"}], user_text="Explain indexes", state=state()
    )
    events = [
        event
        async for event in ReviewedOrchestrator(SimpleNamespace(run_turn=run_turn)).run_turn(**args)
    ]
    assert events == ["original event"] and captured == args


@pytest.mark.parametrize("language", ["en", "de"])
def test_reviewed_answer_passes_project_guard_without_retry(language):
    turn = reviewed_turn(state(language=language))
    from backend.tutor.guard import GuardContext, check

    assert check(turn, GuardContext()) == []


@pytest.mark.parametrize(
    "restriction",
    [
        "No SQL.",
        "Without queries.",
        "Do not propose SQL.",
        "Don't include commands.",
        "Bitte keine SQL-Abfragen.",
        "Ohne SQL.",
        "Keine Abfragen.",
        "Kein Code.",
    ],
)
async def test_reviewed_reuse_honors_no_sql_without_losing_answer_or_history(restriction):
    delegate = SimpleNamespace(run_turn=AsyncMock())
    question = QUESTION + " " + restriction
    before = [{"role": "user", "content": "Keep this earlier research verbatim."}]
    events = [
        event
        async for event in ReviewedOrchestrator(delegate).run_turn(
            history=before, user_text=question, state=state()
        )
    ]
    delegate.run_turn.assert_not_called()
    turn = events[-1].turn
    assert "Table privileges and row policies are separate checks." in turn.text
    assert "normally returns an empty result" in turn.text
    assert "BYPASSRLS" in turn.text
    assert "```sql" not in turn.text and "SELECT current_user" not in turn.text
    assert "These read-only queries" not in turn.text
    assert not turn.ledger_delta and turn.lab_action is None
    assert before == [{"role": "user", "content": "Keep this earlier research verbatim."}]
    assert events[-1].new_messages[0]["content"] == question
    from backend.tutor.guard import GuardContext, check

    assert check(turn, GuardContext()) == []


def test_no_sql_preserves_german_explanation_and_does_not_offer_absent_queries():
    turn = reviewed_turn(state(language="de"), include_diagnostics=False)
    assert "zwei getrennte Prüfungen" in turn.text
    assert "normalerweise ein leeres Ergebnis" in turn.text
    assert "Die folgenden Abfragen" not in turn.text and "```sql" not in turn.text


@pytest.mark.parametrize(
    "language,restriction", [("en", "Do not propose SQL."), ("de", "Bitte keine SQL-Abfragen.")]
)
async def test_reviewed_incident_omits_queries_only_when_requested(language, restriction):
    delegate = SimpleNamespace(run_turn=AsyncMock())
    user_text = "Our SELECT fails: permission denied for table orders. " + restriction
    events = [
        event
        async for event in ReviewedOrchestrator(delegate).run_turn(
            history=[], user_text=user_text, state=state(mode="incident", language=language)
        )
    ]
    delegate.run_turn.assert_not_called()
    turn = events[-1].turn
    assert turn.mode == "incident" and turn.language == language
    assert "```sql" not in turn.text and "SELECT current_user" not in turn.text
    assert (
        "table permission error" in turn.text
        if language == "en"
        else "Tabellenberechtigungsfehler" in turn.text
    )
    assert not turn.ledger_delta and turn.lab_action is None
    assert events[-1].new_messages[0]["content"] == user_text


@pytest.mark.parametrize("restriction", ["Do not show SQL.", "Without commands.", "Ohne SQL."])
async def test_output_restriction_is_not_a_negated_deadlock_report(restriction):
    from app.integrations.supabase_incidents import select_plan

    report = "ERROR: deadlock detected. " + restriction
    assert select_plan(report, state(mode="incident")).key == "deadlock"
    assert select_plan("Not a deadlock detected. " + restriction, state(mode="incident")) is None
    delegate = SimpleNamespace(run_turn=AsyncMock())
    events = [
        event
        async for event in ReviewedOrchestrator(delegate).run_turn(
            history=[], user_text=report, state=state(mode="incident")
        )
    ]
    delegate.run_turn.assert_not_called()
    assert "```sql" not in events[-1].turn.text
    assert "deadlock" in events[-1].turn.text.lower()


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("include_diagnostics", [False, True])
def test_neutral_reuse_preserves_explanation_without_lesson_question(language, include_diagnostics):
    lesson = reviewed_turn(state(language=language), include_diagnostics=include_diagnostics)
    neutral = reviewed_turn(
        state(language=language, mode="neutral"), include_diagnostics=include_diagnostics
    )
    assert lesson.next_question
    assert neutral.next_question is None
    assert lesson.next_question not in neutral.text
    assert neutral.text == lesson.text.replace("\n\n" + lesson.next_question, "", 1)
    assert neutral.speech == lesson.speech


@pytest.mark.parametrize(
    "text,mode,objective",
    [
        ("PostgreSQL 18: " + QUESTION, "lesson", None),
        ("PostgreSQL 18: our SELECT has SQLSTATE 42501.", "incident", None),
        (QUESTION, "lesson", "Compare PostgreSQL 17 and 18."),
    ],
)
async def test_reviewed_version_17_answers_delegate_other_requested_editions(text, mode, objective):
    sentinel = object()

    async def streamed(**kwargs):
        yield sentinel

    events = [
        event
        async for event in ReviewedOrchestrator(SimpleNamespace(run_turn=streamed)).run_turn(
            history=[], user_text=text, state=state(mode=mode, objective=objective)
        )
    ]
    assert events == [sentinel]
