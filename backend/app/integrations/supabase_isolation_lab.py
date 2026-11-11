"""Bounded two-connection experiments, exclusively in the disposable local lab DB.

SQL is fixed by this module. Unique per-run fixtures are removed before returning;
existing lab schemas, learner data and role definitions are never modified.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from pydantic import BaseModel, ConfigDict, Field, model_validator


class IsolationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    workers: int = Field(default=2, ge=2, le=20)
    minimum_active: int = Field(default=1, ge=0, le=20)
    first_commit: Literal["a", "b"] = "a"

    @model_validator(mode="after")
    def feasible_minimum(self) -> "IsolationInput":
        if self.minimum_active > self.workers:
            raise ValueError("Minimum active count cannot exceed the starting count")
        return self


class IsolationLabError(RuntimeError):
    """Safe public error; do not expose DSNs or libpq diagnostics to the browser."""


LEVELS = {
    "read committed": "BEGIN ISOLATION LEVEL READ COMMITTED",
    "repeatable read": "BEGIN ISOLATION LEVEL REPEATABLE READ",
    "serializable": "BEGIN ISOLATION LEVEL SERIALIZABLE",
}
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_EXPERIMENT_LOCK = asyncio.Semaphore(1)


def validate_lab_target(lab_url: str) -> None:
    try:
        fields = conninfo_to_dict(lab_url)
    except psycopg.Error as error:
        raise IsolationLabError("The local lab connection is unavailable") from error
    host = fields.get("host", "")
    if (
        fields.get("dbname") != "lab"
        or fields.get("hostaddr", "127.0.0.1") not in {"127.0.0.1", "::1"}
        or not (isinstance(host, str) and (host in _LOCAL_HOSTS or host.startswith("/")))
    ):
        raise IsolationLabError("This experiment requires the local disposable lab database")


async def _close(conn: Any) -> None:
    if conn is not None and not conn.closed:
        try:
            await conn.execute("ROLLBACK")
        finally:
            await conn.close()


async def _begin(conn: Any, level: str) -> None:
    await conn.execute(LEVELS[level])
    await conn.execute("SET LOCAL ROLE authenticated")
    await conn.execute("SET LOCAL search_path = pg_catalog")
    await conn.execute("SET LOCAL statement_timeout = 1000")
    await conn.execute("SET LOCAL lock_timeout = 1000")
    await conn.execute("SET LOCAL idle_in_transaction_session_timeout = 5000")


async def _read(conn: Any, table: sql.Composed, level: str) -> dict[str, Any]:
    cursor = await conn.execute(
        sql.SQL(
            "SELECT count(*)::integer, current_setting('transaction_isolation'), "
            "pg_current_snapshot()::text, current_user FROM {} WHERE active"
        ).format(table)
    )
    row = await cursor.fetchone()
    if row is None or row[1] != level or row[3] != "authenticated":
        raise IsolationLabError("The lab did not confirm the requested transaction conditions")
    return {"count": row[0], "snapshot": row[2], "isolation": row[1], "role": row[3]}


def _failure(error: psycopg.Error, stage: str) -> dict[str, str | None]:
    if error.sqlstate != "40001":
        raise IsolationLabError(
            "The experiment returned an unexpected transaction error"
        ) from error
    return {"stage": stage, "sqlstate": error.sqlstate}


async def _trial(
    admin: Any,
    lab_url: str,
    table: sql.Composed,
    values: IsolationInput,
    level: str,
    retry: Literal["none", "full", "update_only"],
) -> dict[str, Any]:
    await admin.execute(sql.SQL("TRUNCATE {}").format(table))
    await admin.execute(
        sql.SQL("INSERT INTO {} SELECT id, true FROM generate_series(1, %s) AS workers(id)").format(
            table
        ),
        (values.workers,),
    )
    connections: dict[str, Any] = {}
    observed: dict[str, Any] = {}
    retry_observed = None
    update = sql.SQL("UPDATE {} SET active=false WHERE id=%s").format(table)
    order = [values.first_commit, "b" if values.first_commit == "a" else "a"]
    try:
        for name in ("a", "b"):
            conn = await psycopg.AsyncConnection.connect(
                lab_url,
                autocommit=True,
                connect_timeout=3,
                application_name="audhs-local-isolation-lab",
            )
            connections[name] = conn
            await _begin(conn, level)
        # Both actual reads finish before either transaction writes.
        for name, conn in connections.items():
            read = await _read(conn, table, level)
            if read["count"] != values.workers:
                raise IsolationLabError("The isolated fixture did not match its starting count")
            observed[name] = {
                "read": read,
                "decision": read["count"] > values.minimum_active,
                "updated": 0,
                "committed": False,
                "error": None,
            }
        for name, conn in connections.items():
            if not observed[name]["decision"]:
                continue
            try:
                cursor = await conn.execute(update, (1 if name == "a" else 2,))
                observed[name]["updated"] = cursor.rowcount
            except psycopg.Error as error:
                observed[name]["error"] = _failure(error, "update")
                await conn.execute("ROLLBACK")
        for name in order:
            if observed[name]["error"] is not None:
                continue
            try:
                await connections[name].execute("COMMIT")
                observed[name]["committed"] = True
            except psycopg.Error as error:
                observed[name]["error"] = _failure(error, "commit")
                await connections[name].execute("ROLLBACK")
        before_retry = (
            await (
                await admin.execute(
                    sql.SQL("SELECT count(*)::integer FROM {} WHERE active").format(table)
                )
            ).fetchone()
        )[0]
        expected = values.workers - sum(t["updated"] for t in observed.values() if t["committed"])
        if before_retry != expected:
            raise IsolationLabError("The observed commits do not explain the final fixture")
        victims = [
            name
            for name, t in observed.items()
            if t["error"] is not None and t["error"]["sqlstate"] == "40001"
        ]
        if retry != "none" and len(victims) == 1:
            name = victims[0]
            conn = connections[name]
            await _begin(conn, level)
            retry_read = await _read(conn, table, level) if retry == "full" else None
            # update_only deliberately reuses the old decision, ONLY in this disposable fixture.
            decision = (
                retry_read["count"] > values.minimum_active
                if retry_read is not None
                else observed[name]["decision"]
            )
            changed = (
                (await conn.execute(update, (1 if name == "a" else 2,))).rowcount if decision else 0
            )
            await conn.execute("COMMIT")
            retry_observed = {
                "transaction": name,
                "strategy": retry,
                "read": retry_read,
                "decision": decision,
                "updated": changed,
                "committed": True,
            }
        final_active = (
            await (
                await admin.execute(
                    sql.SQL("SELECT count(*)::integer FROM {} WHERE active").format(table)
                )
            ).fetchone()
        )[0]
        expected_final = before_retry - (retry_observed["updated"] if retry_observed else 0)
        if final_active != expected_final:
            raise IsolationLabError("The retry does not explain the observed final fixture")
        return {
            "level": level,
            "retry_strategy": retry,
            "requested_commit_order": order,
            "transactions": observed,
            "active_before_retry": before_retry,
            "retry": retry_observed,
            "final_active": final_active,
            "minimum_satisfied": final_active >= values.minimum_active,
        }
    finally:
        await asyncio.gather(
            *(_close(conn) for conn in connections.values()), return_exceptions=True
        )


async def _cleanup(admin: Any, schema: sql.Identifier, table: sql.Composed, created: bool) -> None:
    try:
        async with asyncio.timeout(3):
            if created:
                # RESTRICT keeps unexpected dependencies outside this fixture untouched.
                await admin.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(table))
                await admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {}").format(schema))
    except (psycopg.Error, TimeoutError) as error:
        raise IsolationLabError("The disposable fixture could not be removed") from error
    finally:
        await admin.close()


TRIALS: tuple[tuple[str, Literal["none", "full", "update_only"]], ...] = (
    ("read committed", "none"),
    ("repeatable read", "none"),
    ("serializable", "none"),
    ("serializable", "full"),
    ("serializable", "update_only"),
)


@asynccontextmanager
async def isolated_fixture(
    lab_url: str, fixture: Literal["workers", "wallet"]
) -> AsyncIterator[tuple[Any, sql.Composed, str]]:
    """Provide a fresh two-session fixture; only fixed internal tables are supported."""
    validate_lab_target(lab_url)
    async with _EXPERIMENT_LOCK:
        admin = None
        created = False
        schema = sql.Identifier("audhs_isolation_" + uuid4().hex)
        table = sql.SQL("{}.{}").format(schema, sql.Identifier(fixture))
        try:
            async with asyncio.timeout(10):
                admin = await psycopg.AsyncConnection.connect(
                    lab_url,
                    autocommit=True,
                    connect_timeout=3,
                    application_name="audhs-local-isolation-lab",
                )
                target = await (
                    await admin.execute(
                        "SELECT pg_catalog.current_database(), pg_catalog.current_setting('server_version')"
                    )
                ).fetchone()
                if target is None or target[0] != "lab":
                    raise IsolationLabError("This experiment requires the disposable lab database")
                await admin.execute("SET statement_timeout = 1000")
                await admin.execute("SET lock_timeout = 1000")
                await admin.execute("SET search_path = pg_catalog")
                # Record cleanup intent before DDL, including cancellation during its acknowledgement.
                created = True
                try:
                    await admin.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
                except psycopg.errors.DuplicateSchema:
                    created = False  # A collision is not our fixture to remove.
                    raise
                columns = sql.SQL(
                    "active boolean NOT NULL"
                    if fixture == "workers"
                    else "balance integer NOT NULL"
                )
                await admin.execute(
                    sql.SQL("CREATE TABLE {} (id integer PRIMARY KEY, {})").format(table, columns)
                )
                await admin.execute(
                    sql.SQL("GRANT USAGE ON SCHEMA {} TO authenticated").format(schema)
                )
                await admin.execute(
                    sql.SQL("GRANT SELECT, UPDATE ON {} TO authenticated").format(table)
                )
                yield admin, table, target[1]
        except (psycopg.Error, TimeoutError) as error:
            raise IsolationLabError(
                "The disposable transaction experiment could not complete"
            ) from error
        finally:
            if admin is not None:
                cleanup = asyncio.create_task(_cleanup(admin, schema, table, created))
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    await cleanup
                    raise


async def run_isolation_experiment(lab_url: str, values: IsolationInput) -> dict[str, Any]:
    started = time.perf_counter()
    async with isolated_fixture(lab_url, "workers") as (admin, table, version):
        runs = []
        for level, retry in TRIALS:
            runs.append(await _trial(admin, lab_url, table, values, level, retry))
    return {
        "database": "lab",
        "server_version": version,
        "input": values.model_dump(),
        "runs": runs,
        "schema_removed": True,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
    }
