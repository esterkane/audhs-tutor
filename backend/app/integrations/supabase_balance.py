"""Explicit same-row PostgreSQL experiment. Learner SQL is never executed."""

import asyncio
import json
import re
from contextlib import AsyncExitStack
from typing import Any, Literal
from uuid import uuid4

import psycopg
from psycopg import sql
from pydantic import BaseModel, ConfigDict, Field

from app.integrations.supabase_isolation import IsolationAnswer
from app.integrations.supabase_isolation_lab import IsolationLabError, isolated_fixture
from app.integrations.supabase_reference import lab_scope_note


class BalanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    initial: int = Field(ge=0, le=1_000_000)
    a_debit: int = Field(ge=0, le=1_000_000)
    b_operation: Literal["subtract", "set"]
    b_value: int = Field(ge=0, le=1_000_000)


def parse_balance(text: str) -> BalanceInput | None:
    n = r"(0|[1-9][0-9]{0,6})"
    patterns = (
        rf"Run a local Read Committed balance trial: start {n}, A subtracts {n}, B (subtracts|sets) {n}\.",
        rf"Starte einen lokalen Read-Committed-Kontoversuch: Start {n}, A subtrahiert {n}, B (subtrahiert|setzt) {n}\.",
    )
    for pattern in patterns:
        m = re.fullmatch(pattern, text.strip())
        if m and max(int(m[1]), int(m[2]), int(m[4])) <= 1_000_000:
            return BalanceInput(
                initial=int(m[1]),
                a_debit=int(m[2]),
                b_operation="set" if m[3] in ("sets", "setzt") else "subtract",
                b_value=int(m[4]),
            )
    return None


async def measure_balance(lab_url: str, values: BalanceInput) -> dict[str, Any]:
    async with isolated_fixture(lab_url, "wallet") as (admin, table, version):
        await admin.execute(
            sql.SQL("INSERT INTO {} VALUES (1,%s)").format(table), (values.initial,)
        )
        async with AsyncExitStack() as stack:
            sessions = []
            for _ in range(2):
                conn = await stack.enter_async_context(
                    await psycopg.AsyncConnection.connect(
                        lab_url,
                        autocommit=True,
                        connect_timeout=3,
                        application_name="audhs-balance-lab",
                    )
                )
                await conn.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
                await conn.execute("SET LOCAL ROLE authenticated")
                await conn.execute("SET LOCAL search_path = pg_catalog")
                await conn.execute("SET LOCAL statement_timeout = 4000")
                snap = await (
                    await conn.execute(
                        sql.SQL(
                            "SELECT balance,current_user,current_setting('transaction_isolation') FROM {} WHERE id=1"
                        ).format(table)
                    )
                ).fetchone()
                if snap != (values.initial, "authenticated", "read committed"):
                    raise IsolationLabError(
                        "The requested initial row or isolation was not confirmed"
                    )
                sessions.append(conn)
            a, b = sessions
            relative = sql.SQL(
                "UPDATE {} SET balance=balance-%s WHERE id=1 RETURNING balance"
            ).format(table)
            absolute = sql.SQL("UPDATE {} SET balance=%s WHERE id=1 RETURNING balance").format(
                table
            )
            first = await (await a.execute(relative, (values.a_debit,))).fetchone()
            if first is None or first[0] != values.initial - values.a_debit:
                raise IsolationLabError("The first update was not observed")
            pending = asyncio.create_task(
                b.execute(
                    relative if values.b_operation == "subtract" else absolute, (values.b_value,)
                )
            )
            try:
                async with asyncio.timeout(2):
                    while True:
                        if pending.done():
                            raise IsolationLabError("The second update did not wait for the first")
                        blocked = await (
                            await admin.execute(
                                "SELECT %s=ANY(pg_catalog.pg_blocking_pids(%s))",
                                (a.info.backend_pid, b.info.backend_pid),
                            )
                        ).fetchone()
                        if blocked and blocked[0] is True:
                            break
                        await asyncio.sleep(0.01)
                await a.execute("COMMIT")
                second = await (await pending).fetchone()
                await b.execute("COMMIT")
            finally:
                if not pending.done():
                    pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
        final = await (
            await admin.execute(sql.SQL("SELECT balance FROM {} WHERE id=1").format(table))
        ).fetchone()
        if second is None or final is None or final != second:
            raise IsolationLabError("The committed row did not match the second update")
    return {
        "database": "lab",
        "server_version": version,
        "input": values.model_dump(),
        "schema_removed": True,
        "isolation": "read committed",
        "row_id": 1,
        "b_waited_for_a": True,
        "commit_order": ["a", "b"],
        "a_returned": first[0],
        "b_returned": second[0],
        "final_balance": final[0],
    }


def render_balance(obs: dict[str, Any], values: BalanceInput, german: bool) -> str:
    first = values.initial - values.a_debit
    expected = first - values.b_value if values.b_operation == "subtract" else values.b_value
    if (
        obs.get("input") != values.model_dump()
        or any(type(obs["input"][field]) is not int for field in ("initial", "a_debit", "b_value"))
        or obs.get("database") != "lab"
        or obs.get("schema_removed") is not True
        or obs.get("isolation") != "read committed"
        or type(obs.get("row_id")) is not int
        or obs.get("row_id") != 1
        or obs.get("b_waited_for_a") is not True
        or obs.get("commit_order") != ["a", "b"]
        or not isinstance(obs.get("server_version"), str)
        or not re.match(r"^[0-9]+\.[0-9]+(?:\b|\.)", obs["server_version"])
        or not all(
            type(obs.get(k)) is int and obs[k] == v
            for k, v in (
                ("a_returned", first),
                ("b_returned", expected),
                ("final_balance", expected),
            )
        )
    ):
        raise IsolationLabError("The observed schedule does not match the requested trial")
    final = obs["final_balance"]
    expr = (
        f"balance - {values.b_value}" if values.b_operation == "subtract" else str(values.b_value)
    )
    statement = f"UPDATE wallet SET balance = {expr} WHERE id = 1 RETURNING balance;"
    if german:
        reason = (
            f"B zog {values.b_value} vom bestätigten Wert {first} ab."
            if values.b_operation == "subtract"
            else f"B setzte den festen Wert {values.b_value}."
        )
        return (
            f"**Bestätigter Kontostand: {final}.** PostgreSQL {obs['server_version']}, Read Committed. "
            f"Beide Sitzungen lasen anfangs {values.initial}. A zog {values.a_debit} ab und erhielt {first}. "
            f"B wartete auf As Sperre für dieselbe Zeile. Nach As Commit erfüllte die Zeile weiterhin `id = 1`. "
            f"{reason} Bs UPDATE gab {final} zurück; nach Bs Commit las eine separate Verbindung {final}."
            f"\n\nBs Zuweisung in vereinfachter Form, ohne das temporäre Lab-Schema:\n\n```sql\n{statement}\n```"
        )
    reason = (
        f"B subtracted {values.b_value} from the committed value {first}."
        if values.b_operation == "subtract"
        else f"B assigned the constant {values.b_value}."
    )
    return (
        f"**Committed balance: {final}.** PostgreSQL {obs['server_version']}, Read Committed. "
        f"Both sessions initially read {values.initial}. A subtracted {values.a_debit} and returned {first}. "
        f"B waited for A's lock on the same row. After A committed, the row still matched `id = 1`. "
        f"{reason} B's UPDATE returned {final}; a separate connection read {final} after B committed."
        f"\n\nB’s equivalent assignment, with the temporary lab schema omitted:\n\n```sql\n{statement}\n```"
    )


async def balance_answer(
    text: str, state: Any, ctx: Any, history: list[dict[str, Any]] | None = None
) -> IsolationAnswer | None:
    if (
        state.mode != "neutral"
        or state.delivery != "explicit"
        or state.incident is not None
        or getattr(state, "active_lab", None) is not None
    ):
        return None
    values = parse_balance(text)
    if values is None:
        return None
    from app.integrations.supabase_project import project_module

    module = project_module()
    german = state.language == "de"
    args = values.model_dump()
    identity = "balance-" + str(uuid4())
    try:
        lab_url = getattr(getattr(ctx, "lab", None), "lab_url", None)
        if not isinstance(lab_url, str):
            raise IsolationLabError("Lab unavailable")
        evidence = await measure_balance(lab_url, values)
        body = render_balance(evidence, values, german)
        scope = lab_scope_note(evidence["server_version"], text, state, history)
        if scope:
            body = scope + "\n\n" + body
        payload = json.dumps(evidence, ensure_ascii=False)
        failed = False
    except IsolationLabError:
        body = (
            "Der Versuch konnte nicht bestätigt werden. Es liegt kein gemessenes Ergebnis vor."
            if german
            else "The trial could not be verified. No measured balance is available."
        )
        payload = body
        failed = True
    msgs: list[dict[str, Any]] = [
        {"role": "user", "content": text},
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": identity, "name": "same_row_balance_lab", "input": args}
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": identity,
                    "is_error": failed,
                    "content": payload,
                }
            ],
        },
        {"role": "assistant", "content": body},
    ]
    turn = module.TutorTurn(
        mode=state.mode,
        language=state.language,
        persona_on=state.persona_on,
        text=body,
        speech=body.split("\n\n```")[0],
        citations=[],
    )
    return IsolationAnswer(turn, msgs, [("same_row_balance_lab", args, failed)])
