import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def indexer(monkeypatch, tmp_path):
    scripts = Path(__file__).resolve().parents[2] / "integrations/supabase-tutor/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "reference_retirement_test", scripts / "ingest_llms.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "RAW_DIR", tmp_path / "corpus")
    return module


def test_empty_index_never_opens_a_retirement_connection(indexer, monkeypatch):
    import psycopg

    def unexpected(*args, **kwargs):
        pytest.fail("An empty index cannot authorize retiring the corpus")

    monkeypatch.setattr(psycopg, "connect", unexpected)
    assert indexer.retire_missing([]) == 0


@pytest.mark.parametrize(
    "index_url", ["file:///tmp/index", "https://user:password@example.invalid/index"]
)
def test_invalid_index_origin_cannot_authorize_retirement(indexer, index_url):
    with pytest.raises(ValueError, match="credential-free HTTP origin"):
        indexer.retire_missing(["https://supabase.com/keep"], index_url)


@pytest.mark.skipif(
    os.environ.get("AUDHS_POSTGRES_ACCURACY") != "1",
    reason="Opt-in disposable PostgreSQL fixture with locally installed image",
)
def test_actual_postgres_retirement_keeps_other_origins_and_failed_fetch_urls(indexer, monkeypatch):
    import psycopg
    from psycopg import sql

    from tests.test_postgres_accuracy_command import accuracy

    with accuracy.Database() as db:
        db.sql(
            "CREATE SCHEMA tutor; CREATE TABLE tutor.docs_source(url text PRIMARY KEY,status text); "
            "INSERT INTO tutor.docs_source VALUES "
            "('https://supabase.com/keep','active'),('https://supabase.com/missing','active'),"
            "('https://supabase.com/temporary-fetch-failure','active'),"
            "('https://www.postgresql.org/docs/17/sql-grant.html','active'),"
            "('https://supabase.com.evil.invalid/unrelated','active')"
        )

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def execute(self, query, parameters):
                segments = query.split("%s")
                statement = sql.SQL(segments[0])
                for parameter, tail in zip(parameters, segments[1:], strict=True):
                    statement += sql.Literal(parameter) + sql.SQL(tail)
                result = db.sql(statement.as_string() + " RETURNING url")
                return SimpleNamespace(rowcount=len(result.splitlines()) if result else 0)

        monkeypatch.setattr(psycopg, "connect", lambda *args, **kwargs: Connection())
        monkeypatch.setattr(indexer, "admin_url", lambda: "unused-fixture-only")
        count = indexer.retire_missing(
            ["https://supabase.com/keep", "https://supabase.com/temporary-fetch-failure"]
        )
        assert count == 1
        states = dict(
            line.rsplit("|", 1)
            for line in db.sql("SELECT url,status FROM tutor.docs_source ORDER BY url").splitlines()
        )
        assert states["https://supabase.com/missing"] == "retired"
        assert states["https://supabase.com/temporary-fetch-failure"] == "active"
        assert states["https://www.postgresql.org/docs/17/sql-grant.html"] == "active"
        assert states["https://supabase.com.evil.invalid/unrelated"] == "active"


@pytest.mark.parametrize("sdk", ["js", "python", "dart", "swift", "kotlin", "csharp"])
def test_sdk_sources_use_the_searchable_api_product(indexer, sdk):
    assert indexer.product_of(f"https://supabase.com/llms/{sdk}.txt") == "api"


@pytest.mark.parametrize(
    "arguments,failed_sdk,should_retire,expected_count",
    [
        (["--profile", "support"], False, False, 1),
        (["--profile", "all"], False, True, 2),
        (["--profile", "all"], True, False, 1),
        (["--profile", "all", "--only", "cli"], False, False, 1),
    ],
)
async def test_refresh_retirement_respects_selected_coverage(
    indexer, monkeypatch, capsys, arguments, failed_sdk, should_retire, expected_count
):
    from unittest.mock import Mock

    import httpx

    cli = "https://supabase.com/llms/cli.txt"
    dart = "https://supabase.com/llms/dart.txt"

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, **kwargs):
            return httpx.Response(
                200, text=f"# Index\n{cli}\n{dart}", request=httpx.Request("GET", url)
            )

    async def fetch(client, doc, semaphore):
        if failed_sdk and doc.url == dart:
            doc.status = "failed"
        else:
            doc.text = "# SDK reference\nComplete synthetic reference content."
            doc.hash = "synthetic-hash"
        return doc

    async def embed(texts, provider, client, model):
        return [[0.0] * 768 for _ in texts]

    upsert = Mock(return_value=1)
    retire = Mock(return_value=0)
    monkeypatch.setattr(sys, "argv", ["ingest", *arguments])
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "ollama")
    monkeypatch.setattr(indexer.httpx, "AsyncClient", Client)
    monkeypatch.setattr(indexer, "fetch", fetch)
    monkeypatch.setattr(indexer, "embed", embed)
    monkeypatch.setattr(indexer, "existing_hashes", lambda: {})
    monkeypatch.setattr(indexer, "upsert", upsert)
    monkeypatch.setattr(indexer, "retire_missing", retire)
    result = await indexer.main()
    assert result == (1 if failed_sdk else 0)
    assert upsert.call_count == expected_count
    assert retire.called is should_retire
    if should_retire:
        # A complete seed scan can retire truly absent same-origin sources.
        assert set(retire.call_args.args[0]) == {cli, dart}
        assert retire.call_args.args[1] == indexer.INDEX_DEFAULT
    if failed_sdk:
        assert "retirement skipped" in capsys.readouterr().out


@pytest.mark.parametrize(
    "args, index_text",
    [
        (["--profile", "all"], "An upstream maintenance notice without any document links."),
        (["--only", "no-matching-topic", "--verbose"], "https://supabase.com/llms/cli.txt"),
    ],
)
async def test_empty_coverage_fails_cleanly_before_any_embedding_or_retirement(
    indexer, monkeypatch, capsys, args, index_text
):
    from unittest.mock import AsyncMock, Mock

    import httpx

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=index_text))
    monkeypatch.setattr(indexer.httpx, "AsyncClient", lambda: real_client(transport=transport))
    monkeypatch.setattr(sys, "argv", ["ingest", *args])
    monkeypatch.setattr(indexer, "existing_hashes", lambda: {})
    embed, upsert, retire = AsyncMock(), Mock(), Mock()
    monkeypatch.setattr(indexer, "embed", embed)
    monkeypatch.setattr(indexer, "upsert", upsert)
    monkeypatch.setattr(indexer, "retire_missing", retire)
    assert await indexer.main() == 2
    assert "no document URLs" in capsys.readouterr().err
    embed.assert_not_called()
    upsert.assert_not_called()
    retire.assert_not_called()


@pytest.mark.parametrize(
    "stored_model", ["nomic-embed-text", "qwen3-embedding:0.6b", "text-embedding-3-small@768"]
)
async def test_partial_refresh_keeps_existing_space(indexer, monkeypatch, stored_model):
    import hashlib
    from unittest.mock import AsyncMock, Mock

    import httpx

    url = "https://supabase.com/llms/cli.txt"
    body = "# CLI reference\n\nReproducible synthetic reference content."
    digest = hashlib.sha256(body.encode()).hexdigest()
    client = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, text=body if str(r.url) == url else url)
    )
    monkeypatch.setattr(indexer.httpx, "AsyncClient", lambda: client(transport=transport))
    monkeypatch.setattr(sys, "argv", ["ingest", "--only", "cli", "--no-expand"])
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "ollama")
    monkeypatch.setattr(indexer, "existing_hashes", lambda: {url: (digest, 1, stored_model)})
    embed = AsyncMock(return_value=[[0.0] * 768])
    upsert = Mock(return_value=1)
    monkeypatch.setattr(indexer, "embed", embed)
    monkeypatch.setattr(indexer, "upsert", upsert)
    if stored_model == "text-embedding-3-small@768":
        with pytest.raises(ValueError, match="incompatible"):
            await indexer.main()
    else:
        assert await indexer.main() == 0
    embed.assert_not_awaited()
    upsert.assert_not_called()


@pytest.mark.parametrize(
    "model,document_input,query_input",
    [
        ("nomic-embed-text", "search_document: one passage", "search_query: one question"),
        (
            "qwen3-embedding:0.6b",
            "one passage",
            "Instruct: Given a web search query, retrieve relevant passages that answer the query."
            "\nQuery: one question",
        ),
    ],
)
async def test_refresh_and_standalone_query_share_recorded_space(
    indexer, monkeypatch, model, document_input, query_input
):
    import json
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock

    import httpx
    from backend.tutor.retrieval import OllamaEmbedder

    captured = []

    def respond(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"embeddings": [[0.1] * 768]})

    class Pool:
        @asynccontextmanager
        async def connection(self):
            conn = AsyncMock()
            conn.execute.return_value.fetchall.return_value = [(model,)]
            yield conn

    monkeypatch.delenv("EMBEDDINGS_MODEL", raising=False)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        await indexer.embed(["one passage"], "ollama", client, model)
        await OllamaEmbedder(client=client, pool=Pool()).embed_query("one question")
    assert [row["model"] for row in captured] == [model, model]
    assert [row["input"] for row in captured] == [[document_input], [query_input]]
    if model == "qwen3-embedding:0.6b":
        assert all(row["truncate"] is False and row["dimensions"] == 768 for row in captured)


@pytest.mark.parametrize(
    "recorded,configured",
    [
        (["qwen3-embedding:0.6b", "nomic-embed-text"], None),
        (["qwen3-embedding:0.6b"], "nomic-embed-text"),
        ([None], None),
        (["unrecognized"], None),
    ],
)
def test_conflicting_or_unknown_spaces_are_refused(indexer, recorded, configured):
    with pytest.raises(ValueError):
        indexer.resolve_model("ollama", configured, recorded)


def test_upsert_rechecks_identity_under_table_lock_before_any_row_write(indexer, monkeypatch):
    from unittest.mock import MagicMock

    import psycopg

    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchall.return_value = [("qwen3-embedding:0.6b",)]
    monkeypatch.setattr(psycopg, "connect", lambda *_: conn)
    monkeypatch.setattr(indexer, "admin_url", lambda: "synthetic")
    with pytest.raises(ValueError, match="incompatible"):
        indexer.upsert(indexer.Doc("synthetic", 1, "database"), "nomic-embed-text", 1)
    operations = [call.args[0] for call in cur.execute.call_args_list]
    assert operations == [
        "lock table tutor.docs_source in share row exclusive mode",
        indexer.RECORDED_SQL,
    ]


def test_reject_invalid_vector_batches(indexer):
    for batch in [[], [[0.0] * 767], [[float("nan")] * 768], [[float("inf")] * 768]]:
        with pytest.raises(ValueError, match="768"):
            indexer.checked_vectors(batch, 1)


async def test_changed_page_refresh_automatically_keeps_recorded_qwen(indexer, monkeypatch):
    import json
    from unittest.mock import Mock

    import httpx

    url = "https://supabase.com/llms/cli.txt"
    body = "# CLI reference\n\nChanged synthetic reference passage."
    posted = []

    def handle(req):
        if req.method == "POST":
            posted.append(json.loads(req.content))
            return httpx.Response(
                200, json={"embeddings": [[0.3] * 768 for _ in posted[-1]["input"]]}
            )
        return httpx.Response(200, text=body if str(req.url) == url else url)

    client = httpx.AsyncClient
    transport = httpx.MockTransport(handle)
    monkeypatch.setattr(indexer.httpx, "AsyncClient", lambda: client(transport=transport))
    monkeypatch.setattr(sys, "argv", ["ingest", "--only", "cli", "--no-expand"])
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "ollama")
    monkeypatch.delenv("EMBEDDINGS_MODEL", raising=False)
    monkeypatch.setattr(
        indexer, "existing_hashes", lambda: {url: ("old", 1, "qwen3-embedding:0.6b")}
    )
    write = Mock(return_value=1)
    monkeypatch.setattr(indexer, "upsert", write)
    assert await indexer.main() == 0
    assert len(posted) == 1
    assert posted[0]["model"] == "qwen3-embedding:0.6b"
    assert all(not text.startswith("search_document: ") for text in posted[0]["input"])
    assert write.call_args.args[1] == "qwen3-embedding:0.6b"


async def test_html_error_returned_as_success_cannot_retire_or_overwrite(indexer, monkeypatch):
    import httpx
    from unittest.mock import Mock

    url = "https://supabase.com/llms/cli.txt"
    client = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            text="<!DOCTYPE html><html>Service unavailable</html>" if str(req.url) == url else url,
        )
    )
    monkeypatch.setattr(indexer.httpx, "AsyncClient", lambda: client(transport=transport))
    monkeypatch.setattr(sys, "argv", ["ingest", "--profile", "all"])
    monkeypatch.setattr(
        indexer, "existing_hashes", lambda: {url: ("old", 1, "qwen3-embedding:0.6b")}
    )
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "ollama")
    monkeypatch.delenv("EMBEDDINGS_MODEL", raising=False)
    write, retire = Mock(), Mock()
    monkeypatch.setattr(indexer, "upsert", write)
    monkeypatch.setattr(indexer, "retire_missing", retire)
    assert await indexer.main() == 1
    write.assert_not_called()
    retire.assert_not_called()
    assert not indexer.RAW_DIR.exists()


async def test_html_index_with_valid_document_link_stops_before_discovery(indexer, monkeypatch):
    from unittest.mock import Mock
    import httpx

    requested = []

    def handle(request):
        requested.append(str(request.url))
        return httpx.Response(
            200, text="<html><p>Unavailable. Try https://supabase.com/llms/cli.txt </p></html>"
        )

    client = httpx.AsyncClient
    monkeypatch.setattr(
        indexer.httpx, "AsyncClient", lambda: client(transport=httpx.MockTransport(handle))
    )
    monkeypatch.setattr(sys, "argv", ["ingest", "--profile", "all"])
    monkeypatch.setattr(indexer, "existing_hashes", lambda: {})
    retire = Mock()
    monkeypatch.setattr(indexer, "retire_missing", retire)
    assert await indexer.main() == 2
    assert requested == [indexer.INDEX_DEFAULT]
    retire.assert_not_called()
