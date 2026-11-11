import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.integrations.supabase_project import project_module
from app.integrations.supabase_reference import identity_request, reference_answer
from app.integrations.supabase_reviewed import ReviewedOrchestrator

project_module()
from backend.tutor.guard import GuardContext, check  # noqa: E402
from backend.tutor.schemas import Chunk  # noqa: E402
from backend.tutor.tools import ToolContext  # noqa: E402

URL = "https://www.postgresql.org/docs/17/errcodes-appendix.html"


def state(**changes):
    return SimpleNamespace(
        **(
            dict(
                mode="neutral",
                delivery="explicit",
                active_lab=None,
                incident=None,
                language="en",
                persona_on=False,
            )
            | changes
        )
    )


def context(content="| ZZ123 | supplied_condition |", url=URL):
    chunk = Chunk(
        chunk_id=uuid4(),
        url=url,
        heading_path="Error codes",
        content=content,
        tier=2,
        score=1,
        fetched_at=None,
        anchor=None,
    )
    return ToolContext(
        user_id=uuid4(),
        retriever=SimpleNamespace(search=AsyncMock(return_value=[chunk])),
        ledger=None,
    )


@pytest.mark.parametrize(
    "question,codes",
    [
        ("What does SQLSTATE 23514 mean?", ("23514",)),
        ("Was bedeutet SQLSTATE `23514`?", ("23514",)),
        ("What are the condition names for SQLSTATE 23514 and 23502?", ("23514", "23502")),
        ("SQLSTATE 42501, 23514", ("42501", "23514")),
        ("23514", ("23514",)),
    ],
)
def test_only_complete_identity_requests_match(question, codes):
    assert identity_request(question, state()) == codes


@pytest.mark.parametrize(
    "question",
    [
        "Does SQLSTATE 23514 mean not-null? Explain the failing table and a repair.",
        "What does SQLSTATE 23514 mean? Also explain RLS.",
        "SQLSTATE 23514 is this safe to ignore?",
        "Explain the previous error",
        "42501 rows",
        "What does SQLSTATE 23514 mean in PostgreSQL 18?",
        "SQLSTATE ABCDE",
        "SQLSTATE 235140",
        "```SQLSTATE 23514```",
        "SQLSTATE 23514; DROP TABLE private_data",
    ],
)
def test_broader_contextual_and_versioned_questions_do_not_get_partial_answers(question):
    assert identity_request(question, state()) == ()


@pytest.mark.parametrize(
    "changes",
    [
        dict(mode="lesson"),
        dict(mode="exam"),
        dict(delivery="socratic"),
        dict(active_lab=object()),
        dict(incident=object()),
    ],
)
async def test_learning_modes_do_not_bypass_the_tutor(changes):
    ctx = context()
    assert await reference_answer("SQLSTATE ZZ123", state(**changes), ctx) is None
    ctx.retriever.search.assert_not_awaited()


@pytest.mark.parametrize("language", ["de", "en"])
@pytest.mark.parametrize("persona_on", [False, True])
async def test_exact_source_values_and_provenance_without_inference(language, persona_on):
    ctx = context()
    answer = await reference_answer(
        "SQLSTATE ZZ123", state(language=language, persona_on=persona_on), ctx
    )
    assert answer is not None
    assert "`ZZ123` | `supplied_condition`" in answer.turn.text
    assert answer.turn.language == language and answer.turn.persona_on == persona_on
    assert answer.turn.next_question is None and answer.turn.ledger_delta == []
    assert check(answer.turn, GuardContext(sources={URL: 2})) == []
    tool = json.loads(answer.messages[2]["content"][0]["content"])
    assert tool["results"][0]["content"] == "| ZZ123 | supplied_condition |"
    assert answer.messages[-1]["content"] == answer.turn.text
    assert answer.messages[1]["content"][0]["id"] == answer.messages[2]["content"][0]["tool_use_id"]
    ctx.retriever.search.assert_awaited_once_with("SQLSTATE ZZ123", k=12, products=["database"])


@pytest.mark.parametrize(
    "content,url",
    [
        ("| ZZ123 | one_name |\n| ZZ123 | another_name |", URL),
        ("No canonical table row", URL),
        ("| ZZ123 | supplied_condition |", "https://supabase.com/docs/errors"),
        (
            "| ZZ123 | supplied_condition |",
            "https://www.postgresql.org.evil.example/docs/17/errcodes-appendix.html",
        ),
        (
            "| ZZ123 | supplied_condition |",
            "https://www.postgresql.org/docs/current/errcodes-appendix.html",
        ),
    ],
)
async def test_missing_conflicting_or_unqualified_sources_fall_through(content, url):
    assert await reference_answer("SQLSTATE ZZ123", state(), context(content, url)) is None


async def test_never_answer_only_part_of_a_requested_list():
    assert await reference_answer("SQLSTATE ZZ123 and ZZ124", state(), context()) is None


async def test_original_history_is_preserved_and_no_model_call_is_made():
    delegate = SimpleNamespace(run_turn=AsyncMock())
    history = [{"role": "user", "content": "Earlier private findings"}]
    before = copy.deepcopy(history)
    events = [
        e
        async for e in ReviewedOrchestrator(delegate).run_turn(
            history=history, user_text="SQLSTATE ZZ123", state=state(), ctx=context()
        )
    ]
    delegate.run_turn.assert_not_called()
    assert history == before
    assert events[-1].model == "reference:postgres-sqlstate.v1"
    assert events[-1].new_messages[0]["content"] == "SQLSTATE ZZ123"


async def test_mixed_versions_cannot_be_silently_combined():
    ctx = context()
    chunks = await ctx.retriever.search("unused")
    ctx.retriever.search.reset_mock()
    other = chunks[0].model_copy(
        update={"url": URL.replace("/17/", "/18/"), "content": "| ZZ124 | other_condition |"}
    )
    ctx.retriever.search.return_value = chunks + [other]
    assert await reference_answer("SQLSTATE ZZ123 and ZZ124", state(), ctx) is None


@pytest.mark.parametrize("location", ["objective", "history"])
async def test_previous_version_constraints_are_not_lost(location):
    current = state(objective="Use PostgreSQL 18") if location == "objective" else state()
    history = (
        [{"role": "user", "content": "Please use PostgreSQL 18 for this session."}]
        if location == "history"
        else []
    )
    assert await reference_answer("SQLSTATE ZZ123", current, context(), history) is None


async def test_matching_history_version_keeps_source_route_and_original_messages():
    history = [{"role": "user", "content": "We use PostgreSQL 17."}]
    before = copy.deepcopy(history)
    assert await reference_answer("SQLSTATE ZZ123", state(), context(), history) is not None
    assert history == before


async def test_catalogue_does_not_replace_prior_cross_edition_constraint_with_single_major():
    history = [{"role": "user", "content": "Compare PostgreSQL 17 and 18."}]
    assert await reference_answer("SQLSTATE ZZ123", state(), context(), history) is None


async def test_explicit_switch_back_restores_catalogue_on_followup_without_mutating_history():
    history = [
        {"role": "user", "content": "Use PostgreSQL 18."},
        {"role": "user", "content": "Switch back to PostgreSQL 17."},
        {"role": "user", "content": [{"type": "tool_result", "content": "PostgreSQL 18"}]},
    ]
    before = copy.deepcopy(history)
    result = await reference_answer(
        "SQLSTATE ZZ123", state(objective="PostgreSQL 18"), context(), history
    )
    assert result is not None and result.turn.citations[0].url == URL
    assert history == before


async def test_patch_specific_objective_does_not_reuse_major_manual_only():
    assert (
        await reference_answer("SQLSTATE ZZ123", state(objective="PostgreSQL 17.12"), context())
        is None
    )


CONFIG = "https://supabase.com/docs/guides/local-development/cli/config"
QUESTION = "What is the default value for api.max_rows in supabase/config.toml?"


def config_context(value="42", *, url=CONFIG, prefix="", key="api.max_rows"):
    content = (
        f"{prefix}| Name | Default | Required |\n| --- | --- | --- |\n| {key} | {value} | false |"
    )
    ctx = context(content, url)
    hit = ctx.retriever.search.return_value[0]
    ctx.retriever.search.return_value = [hit.model_copy(update={"tier": 1})]
    return ctx


@pytest.mark.parametrize(
    ("text", "lang", "value"),
    [
        (QUESTION, "en", "42"),
        ("Was ist der Standardwert für `api.max_rows` in der Supabase CLI?", "de", "73"),
    ],
)
async def test_config_default_takes_literal_from_source_and_retains_tool_result(text, lang, value):
    ctx = config_context(value, url=CONFIG + "#api.max_rows")
    result = await reference_answer(text, state(language=lang), ctx)
    assert result and result.model == "reference:supabase-config-default.v1"
    assert (
        f"`{value}`" in result.turn.text
        and result.turn.citations[0].url == CONFIG + "#api.max_rows"
    )
    block = result.messages[2]["content"][0]
    assert (
        json.loads(block["content"])["results"][0]["content"]
        == ctx.retriever.search.return_value[0].content
    )
    assert block["tool_use_id"] == result.messages[1]["content"][0]["id"]


@pytest.mark.parametrize(
    "text",
    [
        QUESTION + " What went wrong?",
        "Why did api.max_rows make my request fail?",
        "What is the default for api.max_rows in Supabase CLI v2.1?",
        "What is the default for api.max_rows and auth.enabled in config.toml?",
    ],
)
async def test_config_lookup_does_not_swallow_incidents_or_versions(text):
    ctx = config_context()
    assert await reference_answer(text, state(), ctx) is None
    ctx.retriever.search.assert_not_called()


async def test_config_default_declines_missing_conflicting_historical_or_bad_evidence():
    for ctx in (
        config_context(key="db.port"),
        config_context(url=CONFIG + "#db.port"),
        config_context("None"),
        config_context(prefix="```md\n"),
        config_context(url=URL),
    ):
        assert await reference_answer(QUESTION, state(), ctx) is None
    ctx = config_context("1000")
    ctx.retriever.search.return_value += config_context("500").retriever.search.return_value
    assert await reference_answer(QUESTION, state(), ctx) is None
    for st, hist in [
        (state(objective="Use CLI version 1"), []),
        (state(mode="incident"), []),
        (state(), [{"role": "user", "content": "Use my previous snapshot"}]),
    ]:
        ctx = config_context()
        assert await reference_answer(QUESTION, st, ctx, hist) is None
        ctx.retriever.search.assert_not_called()
