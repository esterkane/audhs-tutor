import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "postgres_accuracy", Path(__file__).resolve().parents[2] / "scripts/postgres_accuracy.py"
)
assert spec is not None and spec.loader is not None
accuracy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accuracy)


def test_foreign_container_is_never_removed(monkeypatch):
    calls = []

    def command(*args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, json.dumps([{"Config": {"Labels": {}}}]))

    monkeypatch.setattr(accuracy, "command", command)
    db = accuracy.Database()
    db.created = True
    with pytest.raises(RuntimeError, match="different fixture identity"):
        db.__exit__(None, None, None)
    assert calls == [("inspect", db.name)]


async def test_arbitrary_isolation_cannot_enter_fixture_sql():
    with pytest.raises(ValueError, match="Unsupported fixture isolation"):
        await accuracy.skew(None, "SERIALIZABLE; DROP SCHEMA public CASCADE")


async def test_missing_barrier_fails_instead_of_reporting_success():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock

    reader = asyncio.StreamReader()
    reader.feed_eof()
    connection = SimpleNamespace(
        stdin=SimpleNamespace(write=Mock(), drain=AsyncMock()), stdout=reader
    )
    with pytest.raises(RuntimeError, match="ended before its barrier"):
        await accuracy.send(connection, "SELECT 1", "finished")


LIVE = pytest.mark.skipif(
    os.environ.get("AUDHS_POSTGRES_ACCURACY") != "1",
    reason="Opt-in disposable Docker fixture; requires an already installed PostgreSQL 17 image",
)


@LIVE
def test_real_sql_results_and_serialization_failure():
    report = accuracy.run()
    assert report["rls"] == {
        "eligible_update_returned": "app_user:original",
        "with_check_failure_sqlstate": "42501",
        "row_after_failure": "app_user:original",
        "using_false_updated_rows": 0,
        "missing_grant_sqlstate": "42501",
    }
    assert report["concurrency"][0]["remaining_on_duty"] == 0
    assert report["concurrency"][1]["second_commit_sqlstate"] == "40001"


@LIVE
def test_unexpected_sql_error_closes_disposable_container():
    db = accuracy.Database()
    with pytest.raises(RuntimeError, match="Fixture SQL failed"):
        with db:
            db.sql("SELECT column_that_does_not_exist")
    assert not db.created
    assert accuracy.command("inspect", db.name, check=False).returncode != 0


@LIVE
def test_startup_observation_error_cleans_only_its_container(monkeypatch):
    original = accuracy.command
    db = accuracy.Database()

    def command(*args, **kwargs):
        if args[0] == "exec" and args[2] == "pg_isready":
            raise subprocess.TimeoutExpired(args, 30)
        return original(*args, **kwargs)

    monkeypatch.setattr(accuracy, "command", command)
    with pytest.raises(subprocess.TimeoutExpired):
        with db:
            pytest.fail("Must not enter unverified database")
    assert not db.created
    assert original("inspect", db.name, check=False).returncode != 0
