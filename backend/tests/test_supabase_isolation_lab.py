import asyncio
from unittest.mock import AsyncMock

import psycopg
import pytest
from pydantic import ValidationError

from app.integrations import supabase_isolation_lab as lab


@pytest.mark.parametrize(
    "payload",
    [
        {"workers": 1},
        {"workers": 21},
        {"workers": True},
        {"minimum_active": True},
        {"workers": 2, "minimum_active": 3},
        {"minimum_active": -1},
        {"first_commit": "COMMIT; DROP DATABASE lab"},
        {"sql": "select 1"},
    ],
)
def test_experiment_rejects_unbounded_or_executable_input(payload):
    with pytest.raises(ValidationError):
        lab.IsolationInput.model_validate(payload)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://localhost/tutor",
        "postgresql://example.test/lab",
        "host=localhost hostaddr=203.0.113.9 dbname=lab",
        "dbname=lab",
        "not a connection string",
    ],
)
async def test_refused_target_never_opens_a_connection(monkeypatch, url):
    connect = AsyncMock()
    monkeypatch.setattr(lab.psycopg.AsyncConnection, "connect", connect)
    with pytest.raises(lab.IsolationLabError):
        await lab.run_isolation_experiment(url, lab.IsolationInput())
    connect.assert_not_awaited()


@pytest.mark.parametrize(
    "url",
    ["postgresql://localhost/lab", "host=/var/run/postgresql dbname=lab", "host=::1 dbname=lab"],
)
def test_only_explicit_local_lab_targets_are_accepted(url):
    lab.validate_lab_target(url)


class Admin:
    def __init__(self, *, database="lab", fail=None):
        self.database = database
        self.fail = fail
        self.statements = []
        self.closed = False

    async def execute(self, query):
        text = query if isinstance(query, str) else query.as_string()
        self.statements.append(text)
        if self.fail and text.startswith(self.fail):
            if self.fail == "CREATE SCHEMA":
                raise asyncio.CancelledError()
            raise psycopg.OperationalError("Synthetic private connection error")
        return self

    async def fetchone(self):
        return self.database, "17.11"

    async def close(self):
        self.closed = True


async def test_actual_database_guard_runs_before_any_fixture_ddl(monkeypatch):
    admin = Admin(database="tutor")
    monkeypatch.setattr(lab.psycopg.AsyncConnection, "connect", AsyncMock(return_value=admin))
    with pytest.raises(lab.IsolationLabError, match="disposable lab database"):
        await lab.run_isolation_experiment("postgresql://localhost/lab", lab.IsolationInput())
    assert admin.closed
    assert len(admin.statements) == 1
    assert admin.statements[0].startswith("SELECT pg_catalog.current_database()")


async def test_cancelled_create_acknowledgement_still_removes_the_unique_fixture(monkeypatch):
    admin = Admin(fail="CREATE SCHEMA")
    monkeypatch.setattr(lab.psycopg.AsyncConnection, "connect", AsyncMock(return_value=admin))
    with pytest.raises(asyncio.CancelledError):
        await lab.run_isolation_experiment("postgresql://localhost/lab", lab.IsolationInput())
    created = next(s for s in admin.statements if s.startswith("CREATE SCHEMA"))
    dropped = next(s for s in admin.statements if s.startswith("DROP SCHEMA"))
    name = created.split('"')[1]
    assert name.startswith("audhs_isolation_") and len(name) == len("audhs_isolation_") + 32
    assert f'"{name}"' in dropped
    assert admin.closed


async def test_cancelled_experiment_waits_for_cleanup_and_keeps_cancellation(monkeypatch):
    admin = Admin()
    started = asyncio.Event()

    async def blocked_trial(*args):
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(lab.psycopg.AsyncConnection, "connect", AsyncMock(return_value=admin))
    monkeypatch.setattr(lab, "_trial", blocked_trial)
    task = asyncio.create_task(
        lab.run_isolation_experiment("postgresql://localhost/lab", lab.IsolationInput())
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert admin.closed
    assert any(s.startswith("DROP SCHEMA IF EXISTS") for s in admin.statements)


async def test_failed_cleanup_cannot_claim_a_successful_experiment(monkeypatch):
    admin = Admin(fail="DROP SCHEMA")
    monkeypatch.setattr(lab.psycopg.AsyncConnection, "connect", AsyncMock(return_value=admin))
    monkeypatch.setattr(lab, "_trial", AsyncMock(return_value={"observed": True}))
    with pytest.raises(lab.IsolationLabError, match="could not be removed"):
        await lab.run_isolation_experiment("postgresql://localhost/lab", lab.IsolationInput())
    assert admin.closed


async def test_namespace_collision_is_never_removed_as_our_fixture(monkeypatch):
    class Collision(Admin):
        async def execute(self, query):
            text = query if isinstance(query, str) else query.as_string()
            if text.startswith("CREATE SCHEMA"):
                self.statements.append(text)
                raise psycopg.errors.DuplicateSchema("Synthetic namespace collision")
            return await super().execute(query)

    admin = Collision()
    monkeypatch.setattr(lab.psycopg.AsyncConnection, "connect", AsyncMock(return_value=admin))
    with pytest.raises(lab.IsolationLabError):
        await lab.run_isolation_experiment("postgresql://localhost/lab", lab.IsolationInput())
    assert admin.closed
    assert not any(s.startswith("DROP") for s in admin.statements)
