import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def indexer(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "integrations/supabase-tutor/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "reference_retirement_test", scripts / "ingest_llms.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
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
