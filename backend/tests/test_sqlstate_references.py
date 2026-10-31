from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.integrations.supabase_project import project_module

project_module()
from backend.tutor.retrieval import (  # noqa: E402
    PgHybridRetriever,
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
    repo, cursor, embedder = retriever([[wrong_code, context, anchor, intro], [anchor]], ranker)
    hits = await repo.search("What does SQLSTATE 42501 mean?", k=4, products=["database"])
    assert hits[0].chunk_id == anchor["chunk_id"] and hits[0].url == url
    assert hits[0].content == "| 42501 | insufficient_privilege |"
    assert len({hit.chunk_id for hit in hits}) == len(hits)
    assert wrong_code["chunk_id"] not in {hit.chunk_id for hit in hits}
    assert context["chunk_id"] in {hit.chunk_id for hit in hits}
    assert intro["chunk_id"] in {hit.chunk_id for hit in hits}
    assert "42601" in anchor["content"]
    embedder.embed_query.assert_awaited_once()
    assert cursor.execute.await_count == 2
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
    repo, cursor, _ = retriever([[], []])
    assert await repo.search("SQLSTATE 42501", products=["auth"]) == []
    parameters = cursor.execute.call_args.args[1]
    assert parameters[2] == parameters[3] == ["auth"]
