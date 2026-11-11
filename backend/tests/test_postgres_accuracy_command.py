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
    assert report["null_comparisons"] == {
        "not_in": [None, False, True, None],
        "not_exists": [True, False, True, True],
    }
    assert report["read_committed"]["absolute_final_balance"] == 80
    assert report["read_committed"]["relative_final_balance"] == 70
    for assignment in ("absolute", "relative"):
        assert report["read_committed"][assignment]["initial_balances"] == [100, 100]
        assert report["read_committed"][assignment]["second_update_wait_observed"] is True
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[2] / "evals/cases/project-postgres-causal.json"
        ).read_text()
    )
    for binding in manifest["oracle_bindings"].values():
        if binding["availability"] != "implemented":
            continue
        observed = report
        for part in binding["report_path"].split("."):
            observed = observed[int(part)] if isinstance(observed, list) else observed[part]
        assert json.dumps(observed) == json.dumps(binding["expected"])


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


def test_null_observations_preserve_unknown_false_and_empty_set_true():
    from types import SimpleNamespace

    expected = {"not_in": [None, False, True, None], "not_exists": [True, False, True, True]}
    db = SimpleNamespace(sql=lambda _: json.dumps(expected))
    assert accuracy.null_comparisons(db) == expected


@pytest.mark.parametrize(
    "observed",
    [
        {"not_in": [False, False, True, None], "not_exists": [True, False, True, True]},
        {"not_in": [None, 0, 1, None], "not_exists": [True, False, True, True]},
        {"not_in": [None, False, None, None], "not_exists": [True, False, True, True]},
        {"not_in": [None, False, True, None]},
    ],
)
def test_wrong_or_missing_null_observations_fail(observed):
    from types import SimpleNamespace

    with pytest.raises(AssertionError, match="NULL fixture"):
        accuracy.null_comparisons(SimpleNamespace(sql=lambda _: json.dumps(observed)))


async def test_arbitrary_assignment_cannot_enter_fixture_sql():
    with pytest.raises(ValueError, match="Unsupported fixture assignment"):
        await accuracy.read_committed_update(None, "absolute; SELECT unsafe")


async def test_wait_barrier_requires_the_exact_blocking_pid():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import Mock

    pending = asyncio.get_running_loop().create_future()
    db = SimpleNamespace(sql=Mock(return_value="t"))
    await accuracy.wait_for_blocker(db, 202, 101, pending)
    db.sql.assert_called_once_with("SELECT 101 = ANY(pg_blocking_pids(202))")
    assert not pending.done()
    pending.cancel()


async def test_completed_update_cannot_be_reported_as_waiting():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import Mock

    completed = asyncio.get_running_loop().create_future()
    completed.set_result("80")
    db = SimpleNamespace(sql=Mock(return_value="t"))
    with pytest.raises(AssertionError, match="ended before its blocker"):
        await accuracy.wait_for_blocker(db, 202, 101, completed)
    db.sql.assert_not_called()


async def test_missing_lock_wait_barrier_is_a_bounded_failure(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import Mock

    times = iter((0, 0, 6))
    monkeypatch.setattr(accuracy, "time", SimpleNamespace(monotonic=lambda: next(times)))

    async def no_sleep(_):
        return None

    monkeypatch.setattr(accuracy.asyncio, "sleep", no_sleep)
    pending = asyncio.get_running_loop().create_future()
    db = SimpleNamespace(sql=Mock(return_value="f"))
    with pytest.raises(RuntimeError, match="required lock-wait barrier"):
        await accuracy.wait_for_blocker(db, 202, 101, pending)
    assert db.sql.call_count == 1
    pending.cancel()


async def test_read_committed_barrier_failure_cleans_up_both_connections(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock

    connections = [
        SimpleNamespace(returncode=None, kill=Mock(), wait=AsyncMock(return_value=0))
        for _ in range(2)
    ]
    monkeypatch.setattr(
        accuracy.asyncio, "create_subprocess_exec", AsyncMock(side_effect=connections)
    )
    pid = 100

    async def send(connection, query, marker):
        nonlocal pid
        if "pg_backend_pid" in query:
            pid += 1
            return str(pid)
        if query.startswith("SELECT balance"):
            return "100"
        if connection is connections[0]:
            return "90"
        await asyncio.get_running_loop().create_future()

    monkeypatch.setattr(accuracy, "send", send)
    monkeypatch.setattr(
        accuracy, "wait_for_blocker", AsyncMock(side_effect=RuntimeError("fixture barrier failed"))
    )
    db = SimpleNamespace(sql=Mock(), arguments=lambda **_: ["unused"])
    with pytest.raises(RuntimeError, match="fixture barrier failed"):
        await accuracy.read_committed_update(db, "absolute")
    for connection in connections:
        connection.kill.assert_called_once()
        connection.wait.assert_awaited_once()


@LIVE
def test_stale_balance_predicate_skips_both_assignments_after_wait():
    import asyncio

    with accuracy.Database() as db:
        db.sql(
            "CREATE SCHEMA accuracy; CREATE TABLE accuracy.balance(id integer primary key, balance integer)"
        )
        for assignment in ("absolute", "relative"):
            observed = asyncio.run(
                accuracy.read_committed_update(db, assignment, require_initial_balance=True)
            )
            assert observed == {
                "initial_balances": [100, 100],
                "second_update_wait_observed": True,
                "second_update_returned": None,
                "final_balance": 90,
            }
