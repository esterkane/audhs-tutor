from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.integrations.supabase_incidents import PLANS, incident_turn, select_plan
from app.integrations.supabase_reviewed import ReviewedOrchestrator

REPORTS = [
    "Our SELECT fails: permission denied for table orders. A policy exists.",
    "Our request fails: permission denied for schema customer_data",
    'Our query fails: relation "orders" does not exist',
    'Our query fails: column "policy_id" does not exist',
    'Our INSERT fails: new row violates row-level security policy for table "orders"',
]


def state(**changes):
    return SimpleNamespace(
        **(
            dict(mode="incident", language="en", persona_on=False, active_lab=None, incident=None)
            | changes
        )
    )


@pytest.mark.parametrize("index", range(5))
@pytest.mark.parametrize("language", ["en", "de"])
def test_report_maps_to_reviewed_plan_and_preserves_incident(index, language):
    current = state(language=language, incident=object())
    plan = select_plan(REPORTS[index], current)
    assert plan == PLANS[index]
    turn = incident_turn(REPORTS[index], current, plan)
    assert turn.mode == "incident" and turn.language == language
    assert turn.incident is not None and not turn.ledger_delta and turn.lab_action is None
    assert not turn.incident.evidence and turn.incident.root_cause is None
    assert "```sql" in turn.text and "policy_id" not in turn.text
    assert "has_table_privilege('public.orders','authenticated')" not in turn.text
    from backend.tutor.guard import GuardContext, check

    assert check(turn, GuardContext()) == []


@pytest.mark.parametrize(
    "report",
    [
        "Our connection times out",
        "We no longer see permission denied for table orders",
    ],
)
def test_ambiguous_or_resolved_report_delegates(report):
    assert select_plan(report, state()) is None


@pytest.mark.parametrize("mode", ["exam", "lesson", "neutral"])
def test_does_not_reinterpret_nonincident_modes(mode):
    assert select_plan(REPORTS[0], state(mode=mode)) is None


async def test_incident_answer_has_no_model_call_and_preserves_history():
    delegate = SimpleNamespace(run_turn=AsyncMock())
    history = [{"role": "assistant", "content": "Prior research and learner correction"}]
    events = [
        event
        async for event in ReviewedOrchestrator(delegate).run_turn(
            history=history, user_text=REPORTS[0], state=state()
        )
    ]
    delegate.run_turn.assert_not_called()
    assert history[0]["content"] == "Prior research and learner correction"
    assert events[-1].new_messages[0]["content"] == REPORTS[0]
    assert events[-1].model == "reviewed:incident-table_privilege.v1"


def test_does_not_ask_for_the_role_already_reported():
    text = "Our SELECT as authenticated fails: permission denied for table orders"
    current = state()
    plan = select_plan(text, current)
    turn = incident_turn(text, current, plan)
    assert (
        turn.next_question == "What exact query and complete error were observed under that role?"
    )


def test_42501_alone_is_not_misdiagnosed_as_missing_table_grant():
    current = state()
    plan = select_plan("Our SELECT has SQLSTATE 42501", current)
    assert plan.key == "insufficient_privilege"
    turn = incident_turn("Our SELECT has SQLSTATE 42501", current, plan)
    assert "code alone does not distinguish" in turn.text
    assert turn.incident.root_cause is None


def test_specific_message_takes_precedence_over_shared_sqlstate():
    plan = select_plan(
        "Our request: SQLSTATE 42501, permission denied for schema private_data", state()
    )
    assert plan.key == "schema_privilege"


@pytest.mark.parametrize("language", ["en", "de"])
def test_mixed_errors_are_explained_separately_without_invented_shared_cause(language):
    report = 'Our query: permission denied for table x; relation "y" does not exist'
    current = state(language=language)
    plan = select_plan(report, current)
    assert plan.key == "mixed_table_privilege_missing_relation"
    turn = incident_turn(report, current, plan)
    assert turn.incident.root_cause is None and not turn.incident.evidence
    assert plan.sql.count("SELECT current_user;") == 1
    assert "current_database()" in plan.sql
    from backend.tutor.guard import GuardContext, check

    assert check(turn, GuardContext()) == []


@pytest.mark.parametrize(
    "report,key",
    [
        ("Our query fails SQLSTATE 42P01", "missing_relation"),
        ("Our query fails SQLSTATE 42703", "missing_column"),
        ("Our requests have SQLSTATE 42P01 and 42703", "mixed_missing_relation_missing_column"),
    ],
)
def test_code_only_reports_reuse_verified_catalog_plans(report, key):
    assert select_plan(report, state()).key == key


def test_mixed_codes_do_not_drop_the_ambiguous_permission_error():
    plan = select_plan("Our query has SQLSTATE 42P01 and 42501", state())
    assert plan.key == "mixed_missing_relation_insufficient_privilege"
    assert "code alone does not distinguish" in plan.english


@pytest.mark.parametrize(
    "report,key",
    [
        (
            "Our transaction fails SQLSTATE 40001. Should I retry only the failed statement?",
            "serialization_failure",
        ),
        ("Our transaction fails SQLSTATE: [40P01]", "deadlock"),
        ("ERROR: could not serialize access due to concurrent update", "serialization_failure"),
        ("ERROR: deadlock detected", "deadlock"),
    ],
)
@pytest.mark.parametrize("language", ["en", "de"])
def test_concurrency_reports_explain_full_transaction_retry_without_invented_sql(
    report, key, language
):
    current = state(language=language)
    plan = select_plan(report, current)
    assert plan.key == key
    turn = incident_turn(report, current, plan)
    assert "```sql" not in turn.text
    assert (
        "complete transaction" in turn.text
        if language == "en"
        else "vollständige Transaktion" in turn.text
    )
    assert turn.incident.root_cause is None and not turn.incident.evidence
    assert not turn.ledger_delta and turn.lab_action is None
    from backend.tutor.guard import GuardContext, check

    assert check(turn, GuardContext()) == []


@pytest.mark.parametrize(
    "report",
    [
        "The invoice number is 40001",
        "A lock timeout occurred",
        "SQLSTATE 57014",
        "We never received SQLSTATE 40001",
        "SQLSTATE 40P01 was not returned",
        "What if SQLSTATE 40001 occurs?",
        "SQLSTATE 40001 and SQLSTATE 23505",
    ],
)
def test_concurrency_reuse_declines_unhandled_hypothetical_or_unreported_errors(report):
    assert select_plan(report, state()) is None


def test_mixed_concurrency_keeps_both_distinctions_without_empty_sql_block():
    report = "Our transactions failed SQLSTATE 40001 and SQLSTATE 40P01"
    current = state()
    plan = select_plan(report, current)
    turn = incident_turn(report, current, plan)
    assert plan.key == "mixed_serialization_failure_deadlock"
    assert "Repeatable Read" in turn.text
    assert "cycle" in turn.text and "lock timeout" in turn.text
    assert not plan.sql and "```sql" not in turn.text
    assert "fixed diagnostic examples" not in turn.text


async def test_concurrency_answer_skips_generation_and_keeps_full_history():
    delegate = SimpleNamespace(run_turn=AsyncMock())
    history = [{"role": "user", "content": "Earlier learner findings"}]
    events = [
        event
        async for event in ReviewedOrchestrator(delegate).run_turn(
            history=history, user_text="ERROR: deadlock detected", state=state()
        )
    ]
    delegate.run_turn.assert_not_called()
    assert history == [{"role": "user", "content": "Earlier learner findings"}]
    assert events[-1].model == "reviewed:incident-deadlock.v1"
    assert events[-1].new_messages[0]["content"] == "ERROR: deadlock detected"


@pytest.mark.parametrize(
    "changes", [{"delivery": "socratic"}, {"active_lab": object()}, {"mode": "exam"}]
)
def test_concurrency_does_not_bypass_chosen_teaching_mode_or_active_lab(changes):
    assert select_plan("Our transaction fails SQLSTATE 40001", state(**changes)) is None
