from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.integrations.supabase_project import project_module

project_module()
from backend.tutor.retrieval import (  # noqa: E402
    PgHybridRetriever,
    named_condition_codes,
    sqlstate_codes,
    sqlstate_excerpt,
)


@pytest.mark.parametrize(
    "query,expected",
    [
        ("What does SQLSTATE 42501 mean?", ("42501",)),
        ("SQLSTATE '42501', '23514' and XX000", ("42501", "23514", "XX000")),
        ("sqlstate: [40p01]", ("40P01",)),
        ("SQLSTATE code: 42501 or 23514", ("42501", "23514")),
        ("42501", ("42501",)),
        ("There were 42501 rows and 23514 updates", ()),
        ("SQLSTATE means an error code", ()),
        ("SQLSTATE 425010", ()),
        ("ABCDE", ()),
    ],
)
def test_explicit_code_identity_not_arbitrary_numbers(query, expected):
    assert sqlstate_codes(query) == expected


def test_excerpt_preserves_exact_header_class_and_requested_row_only():
    source = (
        "| Error Code | Condition Name |\n"
        "| Class 42 - Syntax Error or Access Rule Violation |\n"
        "| 42501 | insufficient_privilege |\n"
        "| 42601 | syntax_error |"
    )
    excerpt = sqlstate_excerpt(source, ("42501",))
    assert excerpt == "\n".join(source.splitlines()[:3])
    assert all(line in source.splitlines() for line in excerpt.splitlines())
    assert sqlstate_excerpt(source, ("23514",)) is None


def row(url, content):
    return dict(
        chunk_id=uuid4(),
        url=url,
        anchor=None,
        heading_path="Synthetic reference",
        content=content,
        tier=2,
        fetched_at=None,
        score=0.1,
    )


def retriever(responses, reranker=None):
    cursor = SimpleNamespace(execute=AsyncMock(), fetchall=AsyncMock(side_effect=responses))
    connection = SimpleNamespace(cursor=lambda **kwargs: cursor)
    context = AsyncMock()
    context.__aenter__.return_value = connection
    pool = SimpleNamespace(connection=lambda: context)
    embedder = SimpleNamespace(embed_query=AsyncMock(return_value=[0.0] * 768))
    return PgHybridRetriever(pool, embedder, reranker), cursor, embedder


async def test_exact_reference_precedes_semantics_and_survives_reranker():
    url = "https://www.postgresql.org/docs/17/errcodes-appendix.html"
    anchor = row(url, "| 42501 | insufficient_privilege |\n| 42601 | syntax_error |")
    wrong_code = row(url, "| 23514 | check_violation |")
    context = row(
        "https://supabase.com/docs/guides/database/postgres/row-level-security", "Other context"
    )
    ranker = SimpleNamespace(
        rerank=AsyncMock(side_effect=lambda q, hits, k: list(reversed(hits))[:k])
    )
    intro = row(url, "General SQLSTATE explanation, without a table")
    repo, cursor, embedder = retriever([[wrong_code, context, anchor, intro], [], [anchor]], ranker)
    hits = await repo.search("What does SQLSTATE 42501 mean?", k=4, products=["database"])
    assert hits[0].chunk_id == anchor["chunk_id"] and hits[0].url == url
    assert hits[0].content == "| 42501 | insufficient_privilege |"
    assert len({hit.chunk_id for hit in hits}) == len(hits)
    assert wrong_code["chunk_id"] not in {hit.chunk_id for hit in hits}
    assert context["chunk_id"] in {hit.chunk_id for hit in hits}
    assert intro["chunk_id"] in {hit.chunk_id for hit in hits}
    assert "42601" in anchor["content"]
    embedder.embed_query.assert_awaited_once()
    assert cursor.execute.await_count == 3
    assert "current_setting('server_version_num')" in cursor.execute.call_args.args[0]
    assert cursor.execute.call_args.args[1][2] == ["database", "cron", "queues"]


async def test_ordinary_search_keeps_existing_one_query_path():
    context = row("https://supabase.com/docs/guides/database", "Ordinary context")
    repo, cursor, embedder = retriever([[context]])
    hits = await repo.search("We inserted 42501 rows", k=8)
    assert hits[0].content == context["content"] and hits[0].chunk_id == context["chunk_id"]
    assert cursor.execute.await_count == 1
    embedder.embed_query.assert_awaited_once()


async def test_explicit_product_filter_is_not_bypassed_for_exact_code():
    repo, cursor, _ = retriever([[], [], []])
    assert await repo.search("SQLSTATE 42501", products=["auth"]) == []
    parameters = cursor.execute.call_args.args[1]
    assert parameters[2] == parameters[3] == ["auth"]


@pytest.mark.parametrize(
    "name,query",
    [
        ("check_violation", "SQLSTATE 42501: is this a check-constraint violation?"),
        ("unique_violation", "Compare SQLSTATE 40001 with a unique violation"),
        ("division_by_zero", "SQLSTATE 22000 and division_by_zero"),
    ],
)
def test_named_comparison_comes_from_supplied_catalogue_rows(name, query):
    content = f"| ZZ123 | {name} |"
    assert named_condition_codes(content, query) == ("ZZ123",)
    assert named_condition_codes(content, "An unrelated question") == ()
    assert named_condition_codes("No canonical table row", query) == ()


async def test_named_comparison_retains_actual_source_identity_and_exact_rows():
    url = "https://www.postgresql.org/docs/17/errcodes-appendix.html"
    first = row(url, "| 42501 | insufficient_privilege |")
    contrast = row(url, "| 23514 | check_violation |\n| 23505 | unique_violation |")
    repo, cursor, _ = retriever([[], [{"content": contrast["content"]}], [first, contrast]])
    hits = await repo.search(
        "Does SQLSTATE 42501 mean a check-constraint violation?", k=4, products=["database"]
    )
    assert [hit.chunk_id for hit in hits] == [first["chunk_id"], contrast["chunk_id"]]
    assert hits[1].content == "| 23514 | check_violation |"
    assert hits[1].url == contrast["url"]
    assert hits[1].tier == contrast["tier"]
    assert "23514" in cursor.execute.call_args.args[1][0]
    assert "23505" not in cursor.execute.call_args.args[1][0]


async def test_sqlstate_tool_search_preserves_original_comparison_terms():
    from backend.tutor.tools import SearchDocsInput, ToolContext, TurnBudget, _search_docs

    repo = SimpleNamespace(search=AsyncMock(return_value=[]))
    original = "Does SQLSTATE 42501 mean a check-constraint violation?"
    ctx = ToolContext(user_id=uuid4(), retriever=repo, ledger=None, learner_text=original)
    await _search_docs(
        SearchDocsInput(query="SQLSTATE 42501 privilege", k=5, products=["database"]),
        ctx,
        TurnBudget(),
    )
    assert repo.search.call_args.args[0] == "SQLSTATE 42501 privilege\n" + original
    assert repo.search.call_args.kwargs == {"k": 5, "products": ["database"]}
    assert ctx.learner_text == original
    repo.search.reset_mock()
    await _search_docs(SearchDocsInput(query="An unrelated topic"), ctx, TurnBudget())
    assert repo.search.call_args.args[0] == "An unrelated topic"


async def test_database_mechanism_keeps_engine_and_framework_sources_without_filter_bypass():
    primary = row(
        "https://www.postgresql.org/docs/17/ddl-rowsecurity.html",
        "Synthetic engine rule with exceptions",
    )
    framework = row(
        "https://supabase.com/docs/guides/database/postgres/functions", "Synthetic framework usage"
    )
    repo, cursor, _ = retriever([[framework], [primary]])
    hits = await repo.search(
        "SECURITY DEFINER privileges and RLS", k=5, products=["database", "auth"]
    )
    assert [hit.chunk_id for hit in hits] == [primary["chunk_id"], framework["chunk_id"]]
    assert hits[0].content == primary["content"]
    assert "current_setting('server_version_num')" in cursor.execute.call_args.args[0]
    assert cursor.execute.call_args.args[1][2] == ["database", "cron", "queues", "auth"]
    repo, cursor, _ = retriever([[framework]])
    await repo.search("SECURITY DEFINER privileges and RLS", k=5, products=["auth"])
    assert cursor.execute.await_count == 1


@pytest.mark.parametrize(
    "query,matched",
    [
        ('"42501" "insufficient_privilege"\nPostgreSQL 17', True),
        ("23514 check_violation", True),
        ("PostgreSQL 17 UPDATE USING 42501 insufficient_privilege permission denied", True),
        ("42501 check_violation", False),
        ("42501 row_count", False),
        ('"42501" "insufficient_privilege" PostgreSQL 18', False),
    ],
)
async def test_code_name_lookup_requires_same_official_row_and_edition(query, matched):
    url = "https://www.postgresql.org/docs/17/errcodes-appendix.html"
    appendix = row(url, "| 42501 | insufficient_privilege |\n| 23514 | check_violation |")
    generic = row("https://supabase.com/docs/example", "Other reference")
    responses = [[generic], [appendix]]
    if matched:
        responses.append([appendix])
    elif "PostgreSQL" in query:
        responses.append([])
    repo, _, _ = retriever(responses)
    hits = await repo.search(query, k=2)
    if matched:
        assert hits[0].url == url
        assert hits[1].chunk_id == generic["chunk_id"]
        assert hits[0].content == next(
            line for line in appendix["content"].splitlines() if line.split("|")[1].strip() in query
        )
    else:
        assert [h.chunk_id for h in hits] == [generic["chunk_id"]]
