import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.integrations.supabase_membership import (
    MembershipRow,
    comparison_sql,
    membership_answer,
    parse_request,
    render,
)
from app.integrations.supabase_project import project_module
from app.integrations.supabase_reviewed import ReviewedOrchestrator

project_module()
from backend.tutor.guard import GuardContext, check  # noqa: E402
from backend.tutor.schemas import Chunk  # noqa: E402
from backend.tutor.tools import ToolContext  # noqa: E402

PREFIX = (
    "Run a local comparison of NOT IN and correlated NOT EXISTS (inner = outer) for outer value "
)
URL = "https://www.postgresql.org/docs/17/functions-subquery.html"
CASES = [
    (2, [1, None], [False, None], [True, None], [], None, True, "TRUE AND UNKNOWN = UNKNOWN"),
    (1, [1, None], [True, None], [False, None], [1], False, False, "FALSE AND UNKNOWN = FALSE"),
    (None, [], [], [], [], True, True, "empty"),
    (None, [None], [None], [None], [], None, True, "UNKNOWN = UNKNOWN"),
]


def state(**changes):
    return SimpleNamespace(
        **(
            dict(
                mode="neutral", delivery="explicit", incident=None, language="en", persona_on=False
            )
            | changes
        )
    )


def evidence(case):
    outer, inner, eq, neq, matches, not_in, not_exists, _ = case
    return dict(
        server_version="17.11",
        outer_value=outer,
        inner_values=inner,
        equality_results=eq,
        inequality_results=neq,
        matching_values=matches,
        not_in=not_in,
        not_exists=not_exists,
    )


def context(row):
    source = Chunk(
        chunk_id=uuid4(),
        url=URL,
        heading_path="Subquery expressions",
        content="Official reference.",
        tier=2,
        score=1,
        fetched_at=None,
        anchor=None,
    )
    return ToolContext(
        user_id=uuid4(),
        retriever=SimpleNamespace(search=AsyncMock(return_value=[source])),
        ledger=None,
        lab=SimpleNamespace(
            run_sql=AsyncMock(return_value={"ok": True, "persisted": False, "rows": [row]})
        ),
    )


@pytest.mark.parametrize(
    "left,right",
    [
        ("true", "[]"),
        ("1.5", "[]"),
        ("0", "[true]"),
        ("0", "[NaN]"),
        ("1000001", "[]"),
        ("0", '["pg_sleep(10)"]'),
        ("0", str([1] * 21)),
        ('2,"inner":[],"outer":3', "[]"),
    ],
)
def test_invalid_literal_inputs_cannot_enter_sql(left, right):
    with pytest.raises((ValidationError, ValueError)):
        parse_request(PREFIX + left + " and inner values " + right + ".")


@pytest.mark.parametrize(
    "question",
    [
        "Explain NOT IN and NOT EXISTS",
        PREFIX + "2 and inner values [1,null]. Also inspect users.",
        "SELECT * FROM private_data",
        "Do not execute anything: " + PREFIX + "2 and inner values [].",
    ],
)
def test_general_questions_are_not_executed(question):
    assert parse_request(question) is None


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("language", ["en", "de"])
async def test_complete_computed_explanation_and_provenance(case, language):
    import json

    question = PREFIX + json.dumps(case[0]) + " and inner values " + json.dumps(case[1]) + "."
    ctx = context(evidence(case))
    answer = await membership_answer(question, state(language=language), ctx)
    assert answer is not None
    assert case[-1] in answer.turn.text if language == "en" else "NOT EXISTS" in answer.turn.text
    assert check(answer.turn, GuardContext(sources={URL: 2}, ran_lab_sql=True)) == []
    assert answer.turn.next_question is None and not answer.turn.ledger_delta
    assert len(answer.messages) == 6
    assert answer.messages[0]["content"] == question
    assert answer.messages[-1]["content"] == answer.turn.text
    request = ctx.lab.run_sql.call_args.args[0]
    assert request.role == "authenticated" and request.persist is False
    assert "ORDER BY i.ord" in request.sql and "WITH ORDINALITY" in request.sql


async def test_inconsistent_results_cannot_be_presented_as_checked():
    row = evidence(CASES[0])
    row["not_in"] = False
    with pytest.raises(AppError, match="inconsistent"):
        await membership_answer(PREFIX + "2 and inner values [1,null].", state(), context(row))


@pytest.mark.parametrize(
    "changes",
    [
        dict(mode="lesson"),
        dict(mode="exam"),
        dict(mode="incident"),
        dict(delivery="socratic"),
        dict(incident=object()),
    ],
)
async def test_learning_modes_and_incidents_are_not_bypassed(changes):
    ctx = context(evidence(CASES[0]))
    assert (
        await membership_answer(PREFIX + "2 and inner values [1,null].", state(**changes), ctx)
        is None
    )
    ctx.lab.run_sql.assert_not_called()


async def test_invalid_values_do_not_execute_or_call_a_model():
    ctx = context(evidence(CASES[0]))
    answer = await membership_answer(
        PREFIX + '0 and inner values ["DROP TABLE users"].', state(), ctx
    )
    assert answer is not None and "20" in answer.turn.text
    ctx.lab.run_sql.assert_not_called()
    ctx.retriever.search.assert_not_called()


async def test_history_preserved_and_no_delegate_generation():
    delegate = SimpleNamespace(run_turn=AsyncMock())
    history = [{"role": "user", "content": "Earlier private finding"}]
    before = copy.deepcopy(history)
    events = [
        e
        async for e in ReviewedOrchestrator(delegate).run_turn(
            history=history,
            user_text=PREFIX + "2 and inner values [1,null].",
            state=state(),
            ctx=context(evidence(CASES[0])),
        )
    ]
    assert events[-1].model == "local:membership-lab.v1"
    assert history == before
    delegate.run_turn.assert_not_called()


def test_fixed_query_only_contains_bounded_literal_values():
    values = parse_request(PREFIX + "-1000000 and inner values [1000000,null].")
    sql = comparison_sql(values)
    assert "-1000000::bigint" in sql and "ARRAY[1000000,NULL]::bigint[]" in sql
    assert "FROM outer_values" in sql and "inner_values" in sql


def test_false_and_unknown_are_distinct_when_rendering():
    false = render(MembershipRow.model_validate(evidence(CASES[1])), False, "")
    unknown = render(MembershipRow.model_validate(evidence(CASES[0])), False, "")
    assert "FALSE AND UNKNOWN = FALSE" in false
    assert "TRUE AND UNKNOWN = UNKNOWN" in unknown


async def test_documentation_outage_does_not_lose_actual_computation():
    ctx = context(evidence(CASES[0]))
    ctx.retriever.search.side_effect = RuntimeError("offline")
    answer = await membership_answer(PREFIX + "2 and inner values [1,null].", state(), ctx)
    assert "TRUE AND UNKNOWN = UNKNOWN" in answer.turn.text
    assert not answer.turn.citations
    assert answer.calls[-1][2] is True
    assert answer.messages[-2]["content"][0]["is_error"] is True


async def test_different_returned_inputs_are_not_presented_as_requested():
    row = evidence(CASES[0])
    row["outer_value"] = 3
    with pytest.raises(AppError, match="different input"):
        await membership_answer(PREFIX + "2 and inner values [1,null].", state(), context(row))


async def test_low_trust_reference_is_not_silently_promoted():
    ctx = context(evidence(CASES[0]))
    chunks = await ctx.retriever.search("setup")
    ctx.retriever.search.return_value = [chunks[0].model_copy(update={"tier": 4})]
    answer = await membership_answer(PREFIX + "2 and inner values [1,null].", state(), ctx)
    assert "TRUE AND UNKNOWN = UNKNOWN" in answer.turn.text
    assert not answer.turn.citations
