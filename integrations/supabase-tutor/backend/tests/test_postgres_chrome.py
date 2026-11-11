import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.tutor.postgres_chrome import CORRECTION, NAV_QUERY, pure_manual_chrome

URL = "https://www.postgresql.org/docs/17/transaction-iso.html"
HEADER = """October 15, 2026: PostgreSQL 19 RC 1 Released!

Documentation → PostgreSQL 17

Supported Versions: Current (18) / 17 / 16 / 15 / 14

Development Versions: 19 / devel

Unsupported versions: 13 / 12 / 11 / 10 / 9.6 / 9.5

| 13.2. Transaction Isolation |
| Prev | Up | Chapter 13. Concurrency Control | Home | Next |"""


def test_only_entire_known_chrome_from_versioned_manual_is_filtered():
    assert pure_manual_chrome(URL, HEADER) and pure_manual_chrome(URL, CORRECTION)
    for passage in (
        HEADER + "\nRead Committed admits different snapshots.",
        "SELECT 1;\n" + CORRECTION,
        "Use Next and Prev to navigate a B-tree.",
        "The catalog id is documented here.",
        "SELECT '" + CORRECTION + "';",
    ):
        assert not pure_manual_chrome(URL, passage)
    for url in (URL.replace("/17/", "/current/"), "https://supabase.com/docs/guides/data.md", URL + "?test"):
        assert not pure_manual_chrome(url, CORRECTION)


def test_navigation_requests_and_technical_uses_of_navigation_words():
    for query in (
        "How do I report a documentation issue?",
        "Which PostgreSQL documentation versions are listed?",
        "PostgreSQL Home Prev Up Next documentation page navigation",
        "Unterstützte PostgreSQL-Versionen im Handbuch",
    ):
        assert NAV_QUERY.search(query)
    for query in (
        "supported transaction isolation levels",
        "Which PostgreSQL versions introduced MERGE?",
        "How does a B-tree navigate from a parent to a child?",
        "current transaction release savepoint",
    ):
        assert not NAV_QUERY.search(query)


async def test_chrome_triggers_bounded_backfill_and_preserves_mixed_passage():
    from contextlib import asynccontextmanager
    from datetime import UTC, datetime
    from uuid import uuid4

    from backend.tutor.retrieval import PgHybridRetriever

    header = {
        "chunk_id": uuid4(),
        "url": URL,
        "anchor": None,
        "heading_path": "",
        "content": HEADER,
        "tier": 2,
        "fetched_at": datetime.now(UTC),
        "score": 0.1,
    }
    useful = dict(header, chunk_id=uuid4(), content="The transaction can be retried.")
    mixed = dict(header, chunk_id=uuid4(), content=HEADER + "\nValid technical detail")

    class Cursor:
        def __init__(self):
            self.calls = []

        async def execute(self, sql, params):
            self.calls.append((sql, params))

        async def fetchall(self):
            return [header, useful] if len(self.calls) < 3 else [header, useful, mixed]

    cursor = Cursor()

    class Connection:
        def cursor(self, **kwargs):
            return cursor

    class Pool:
        @asynccontextmanager
        async def connection(self):
            yield Connection()

    class Embedder:
        async def embed_query(self, query):
            return [0.1] * 768

    hits = await PgHybridRetriever(Pool(), Embedder()).search("transaction outcomes", 2, ["database"])
    assert [h.chunk_id for h in hits] == [useful["chunk_id"], mixed["chunk_id"]]
    assert hits[1].content == mixed["content"]
    assert cursor.calls[1][1][2] == 120
    assert cursor.calls[2][1][1:4] == ([URL], ["database", "cron", "queues"], ["database", "cron", "queues"])
    cursor.calls.clear()
    hits = await PgHybridRetriever(Pool(), Embedder()).search("documentation navigation", 2, ["database"])
    assert [h.chunk_id for h in hits] == [header["chunk_id"], useful["chunk_id"]]
    assert len(cursor.calls) == 1
