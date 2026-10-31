#!/usr/bin/env python3
"""Executable PostgreSQL accuracy fixtures in a new, network-isolated disposable container.

No project database, connection URL, API key, hosted model or image download is used.
Requires Docker and the locally installed Supabase PostgreSQL 17 image. Run from WSL/Linux.
"""

import argparse
import asyncio
import json
import subprocess
import time
from typing import Self
from uuid import uuid4

IMAGE = "public.ecr.aws/supabase/postgres:17.11.0.004"
LABEL = "audhs.accuracy.fixture"
SOURCES = [
    "https://www.postgresql.org/docs/17/sql-createpolicy.html",
    "https://www.postgresql.org/docs/17/transaction-iso.html",
    "https://www.postgresql.org/docs/17/mvcc-serialization-failure-handling.html",
]


def command(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=30, check=check
    )


class Database:
    def __init__(self) -> None:
        self.name = "audhs-accuracy-" + uuid4().hex
        self.created = False
        self.image_id = ""

    def __enter__(self) -> Self:
        image = json.loads(command("image", "inspect", IMAGE).stdout)[0]
        self.image_id = image["Id"]
        if not self.image_id.startswith("sha256:"):
            raise ValueError("Local image must resolve to an immutable ID")
        try:
            command(
                "run",
                "-d",
                "--pull",
                "never",
                "--name",
                self.name,
                "--label",
                LABEL + "=" + self.name,
                "--network",
                "none",
                "--read-only",
                "--memory",
                "256m",
                "--memory-swap",
                "256m",
                "--cpus",
                "1",
                "--pids-limit",
                "64",
                "--tmpfs",
                "/work:rw,size=128m,mode=1777,noexec,nosuid",
                "--user",
                "postgres",
                "--entrypoint",
                "/bin/sh",
                self.image_id,
                "-c",
                "initdb -D /work/data --auth=trust --no-locale >/work/init.log && "
                "exec postgres -D /work/data -k /work -c listen_addresses='' "
                "-c shared_buffers=16MB -c max_connections=10",
            )
            self.created = True
            for _ in range(40):
                ready = command("exec", self.name, "pg_isready", "-h", "/work", check=False)
                if ready.returncode == 0:
                    return self
                time.sleep(0.25)
            raise RuntimeError("Disposable PostgreSQL did not become ready")
        except BaseException:
            if not self.created:
                inspected = command("inspect", self.name, check=False)
                if inspected.returncode == 0:
                    metadata = json.loads(inspected.stdout)[0]
                    self.created = metadata["Config"]["Labels"].get(LABEL) == self.name
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_: object) -> None:
        if self.created:
            metadata = json.loads(command("inspect", self.name).stdout)[0]
            if metadata["Config"]["Labels"].get(LABEL) != self.name:
                raise RuntimeError(
                    "Refusing to remove a container with a different fixture identity"
                )
            command("rm", "-f", self.name)
            self.created = False

    def arguments(self, *, interactive: bool = False) -> list[str]:
        return [
            "docker",
            "exec",
            *(["-i"] if interactive else []),
            self.name,
            "psql",
            "-X",
            "-qAt",
            "-h",
            "/work",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-v",
            "ON_ERROR_STOP=1",
            "-v",
            "VERBOSITY=verbose",
        ]

    def sql(self, query: str, *, expected_state: str | None = None) -> str:
        result = subprocess.run(
            self.arguments() + ["-c", query],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if expected_state is not None:
            if result.returncode == 0 or f"ERROR:  {expected_state}:" not in result.stderr:
                raise AssertionError("Expected SQLSTATE " + expected_state + " was not observed")
            return expected_state
        if result.returncode:
            raise RuntimeError("Fixture SQL failed: " + result.stderr)
        return result.stdout.strip()


async def send(process: asyncio.subprocess.Process, query: str, marker: str) -> str:
    if process.stdin is None or process.stdout is None:
        raise RuntimeError("Missing fixture connection pipes")
    process.stdin.write((query + "; SELECT '" + marker + "';\n").encode())
    await process.stdin.drain()
    lines = []
    while True:
        line = await asyncio.wait_for(process.stdout.readline(), timeout=10)
        if not line:
            raise RuntimeError("Fixture connection ended before its barrier")
        text = line.decode().strip()
        if text == marker:
            return "\n".join(lines)
        lines.append(text)


async def skew(db: Database, isolation: str) -> dict[str, object]:
    # Only fixed developer-owned SQL is executed, never learner/model text.
    if isolation not in {"REPEATABLE READ", "SERIALIZABLE"}:
        raise ValueError("Unsupported fixture isolation")
    db.sql("TRUNCATE accuracy.duty; INSERT INTO accuracy.duty VALUES (1,true),(2,true)")
    connections = []
    try:
        for _ in range(2):
            connections.append(
                await asyncio.create_subprocess_exec(
                    *db.arguments(interactive=True),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )
        for connection in connections:
            snapshot = await send(
                connection,
                "BEGIN ISOLATION LEVEL "
                + isolation
                + "; SELECT count(*) FROM accuracy.duty WHERE on_duty",
                "snapshot",
            )
            if snapshot != "2":
                raise AssertionError("Both transactions must first see two available rows")
        for index, connection in enumerate(connections, 1):
            await send(
                connection,
                f"UPDATE accuracy.duty SET on_duty=false WHERE id={index}",
                "updated",
            )
        await send(connections[0], "COMMIT", "committed")
        second = connections[1]
        if second.stdin is None:
            raise RuntimeError("Missing second connection")
        second.stdin.write(b"COMMIT;\n")
        await second.stdin.drain()
        second.stdin.close()
        _output, error = await asyncio.wait_for(second.communicate(), timeout=10)
        state = "40001" if b"ERROR:  40001:" in error else None
        if isolation == "REPEATABLE READ":
            if second.returncode or state:
                raise AssertionError("Repeatable Read fixture should commit both disjoint writes")
        elif second.returncode == 0 or state != "40001":
            raise AssertionError("Serializable fixture must reject this schedule")
        remaining = int(db.sql("SELECT count(*) FROM accuracy.duty WHERE on_duty"))
        expected = 0 if isolation == "REPEATABLE READ" else 1
        if remaining != expected:
            raise AssertionError("Unexpected committed duty state")
        return {
            "isolation": isolation,
            "initial_counts": [2, 2],
            "remaining_on_duty": remaining,
            "second_commit_sqlstate": state,
        }
    finally:
        for connection in connections:
            if connection.returncode is None:
                connection.kill()
                await connection.wait()


def run() -> dict[str, object]:
    with Database() as db:
        version = db.sql("SHOW server_version")
        if not version.startswith("17."):
            raise RuntimeError("Fixture references require PostgreSQL 17")
        db.sql(
            "CREATE ROLE app_user NOLOGIN; CREATE SCHEMA accuracy; "
            "GRANT USAGE ON SCHEMA accuracy TO app_user; "
            "CREATE TABLE accuracy.documents(id int PRIMARY KEY, owner_id text, body text); "
            "INSERT INTO accuracy.documents VALUES (1,'app_user','original'); "
            "GRANT SELECT,UPDATE ON accuracy.documents TO app_user; "
            "ALTER TABLE accuracy.documents ENABLE ROW LEVEL SECURITY; "
            "CREATE POLICY visible ON accuracy.documents FOR SELECT USING (true); "
            "CREATE POLICY editable ON accuracy.documents FOR UPDATE "
            "USING (owner_id=current_user) WITH CHECK (owner_id=current_user); "
            "CREATE TABLE accuracy.duty(id int PRIMARY KEY,on_duty boolean)"
        )
        eligible = db.sql(
            "SET ROLE app_user; UPDATE accuracy.documents SET body=body WHERE id=1 "
            "RETURNING owner_id||':'||body"
        )
        if eligible != "app_user:original":
            raise AssertionError(
                "The current role must be able to update the eligible existing row"
            )
        rejected = db.sql(
            "SET ROLE app_user; UPDATE accuracy.documents SET owner_id='other_user' WHERE id=1",
            expected_state="42501",
        )
        unchanged = db.sql(
            "SET ROLE app_user; SELECT owner_id||':'||body FROM accuracy.documents WHERE id=1"
        )
        if unchanged != "app_user:original":
            raise AssertionError("Rejected new-row check must leave stored row unchanged")
        db.sql("UPDATE accuracy.documents SET owner_id='other_user' WHERE id=1")
        hidden = db.sql(
            "SET ROLE app_user; WITH changed AS (UPDATE accuracy.documents SET body='changed' "
            "WHERE id=1 RETURNING id) SELECT count(*) FROM changed"
        )
        if hidden != "0":
            raise AssertionError("False UPDATE USING must exclude the existing row")
        db.sql("REVOKE UPDATE ON accuracy.documents FROM app_user")
        missing_grant = db.sql(
            "SET ROLE app_user; UPDATE accuracy.documents SET body='changed' WHERE id=1",
            expected_state="42501",
        )
        return {
            "version": version,
            "image_id": db.image_id,
            "network": "none",
            "sources": SOURCES,
            "rls": {
                "eligible_update_returned": eligible,
                "with_check_failure_sqlstate": rejected,
                "row_after_failure": unchanged,
                "using_false_updated_rows": int(hidden),
                "missing_grant_sqlstate": missing_grant,
            },
            "concurrency": [
                asyncio.run(skew(db, level)) for level in ("REPEATABLE READ", "SERIALIZABLE")
            ],
        }


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(run(), indent=2))
