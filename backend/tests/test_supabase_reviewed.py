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
