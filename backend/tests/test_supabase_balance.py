import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.integrations import supabase_balance as balance
from app.integrations.supabase_isolation_lab import IsolationLabError
from tests.test_supabase_membership import state

EN = "Run a local Read Committed balance trial: start 100, A subtracts 20, B subtracts 30."
DE = "Starte einen lokalen Read-Committed-Kontoversuch: Start 100, A subtrahiert 20, B setzt 70."


def measured(values):
    first = values.initial - values.a_debit
    final = values.b_value if values.b_operation == "set" else first - values.b_value
    return {
        "database": "lab",
        "server_version": "17.11",
        "input": values.model_dump(),
        "schema_removed": True,
        "isolation": "read committed",
        "row_id": 1,
        "b_waited_for_a": True,
        "commit_order": ["a", "b"],
        "a_returned": first,
        "b_returned": final,
        "final_balance": final,
    }


@pytest.mark.parametrize(
    "text",
    [
        EN + " and change isolation.",
        EN.replace("Read Committed", "Repeatable Read"),
        EN.replace("B subtracts 30.", "B subtracts 30 only if balance is still 100."),
        EN.replace("20,", "1000001,"),
        EN.replace("30.", "-1."),
        "Do not execute this: " + EN,
        "What happened to my last balance?",
    ],
)
def test_only_exact_explicit_schedule_runs(text):
    assert balance.parse_balance(text) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("database", "project"),
        ("isolation", "repeatable read"),
        ("row_id", 2),
        ("row_id", True),
        ("b_waited_for_a", False),
        ("commit_order", ["b", "a"]),
        ("a_returned", 70),
        ("b_returned", 80),
        ("final_balance", 80),
        ("schema_removed", False),
        ("server_version", ""),
        ("input", {}),
    ],
)
def test_stale_incomplete_or_inconsistent_observation_is_refused(field, value):
    values = balance.parse_balance(EN)
    obs = measured(values)
    obs[field] = value
    with pytest.raises(IsolationLabError):
        balance.render_balance(obs, values, False)


@pytest.mark.parametrize(
    "text,lang,outcome,sql",
    [
        (EN, "en", "Committed balance: 50", "balance - 30"),
        (DE, "de", "Bestätigter Kontostand: 70", "balance = 70"),
    ],
)
async def test_measured_answer_persists_observed_trial_and_does_not_reuse_stale_history(
    monkeypatch, text, lang, outcome, sql
):
    values = balance.parse_balance(text)
    current = measured(values)
    runner = AsyncMock(return_value=current)
    monkeypatch.setattr(balance, "measure_balance", runner)
    history = [
        {"role": "user", "content": "Use PostgreSQL 18."},
        {"role": "assistant", "content": "All scheduled updates return 80."},
    ]
    before = copy.deepcopy(history)
    ctx = SimpleNamespace(lab=SimpleNamespace(lab_url="postgresql://localhost/lab"))
    result = await balance.balance_answer(text, state(language=lang), ctx, history)
    assert outcome in result.turn.text and sql in result.turn.text
    assert (
        "ohne das temporäre Lab-Schema" if lang == "de" else "temporary lab schema omitted"
    ) in result.turn.text
    assert "18" in result.turn.text and "17.11" in result.turn.text
    assert (
        not result.turn.ledger_delta and not result.turn.next_question and not result.turn.citations
    )
    assert result.messages[0] == {"role": "user", "content": text}
    assert json.loads(result.messages[2]["content"][0]["content"]) == current
    assert result.messages[3]["content"] == result.turn.text and history == before
    runner.assert_awaited_once_with("postgresql://localhost/lab", values)


async def test_no_connection_cannot_return_computed_balance():
    result = await balance.balance_answer(EN, state(), None)
    assert result.calls[0][-1] is True
    assert "50" not in result.turn.text and "No measured balance" in result.turn.text
