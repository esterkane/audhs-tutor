"""Explicit literal-value lab: actual PostgreSQL results, deterministic explanations."""

import json
import logging
import re
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.errors import AppError

Value = Annotated[int, Field(strict=True, ge=-1000000, le=1000000)] | None


class MembershipInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outer: Value
    inner: list[Value] = Field(max_length=20)


class MembershipRow(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    server_version: str
    outer_value: Value
    inner_values: list[Value]
    equality_results: list[bool | None]
    inequality_results: list[bool | None]
    matching_values: list[Value]
    not_in: bool | None
    not_exists: bool


@dataclass(frozen=True)
class MembershipAnswer:
    turn: Any
    messages: list[dict[str, Any]]
    calls: list[tuple[str, dict[str, Any], bool]]


def parse_request(text: str) -> MembershipInput | None:
    if len(text) > 1000:
        return None
    patterns = [
        (
            r"Run a local comparison of NOT IN and correlated NOT EXISTS \(inner = outer\) "
            r"for outer value (.+?) and inner values (\[.*\])\."
        ),
        (
            r"Führe einen lokalen Vergleich von NOT IN und korreliertem NOT EXISTS \(inner = outer\) "
            r"für den äußeren Wert (.+?) "
            r"und die inneren Werte (\[.*\]) aus\."
        ),
    ]
    for pattern in patterns:
        if match := re.fullmatch(pattern, text.strip(), re.IGNORECASE):
            return MembershipInput.model_validate(
                {"outer": json.loads(match[1]), "inner": json.loads(match[2])}
            )
    return None


def comparison_sql(values: MembershipInput) -> str:
    # Only validated bounded integers/null enter these literal positions. No SQL input.
    outer = "NULL" if values.outer is None else str(values.outer)
    inner = ",".join("NULL" if value is None else str(value) for value in values.inner)
    return f"""WITH outer_values AS (SELECT {outer}::bigint AS value),
inner_values AS (SELECT value, ord FROM pg_catalog.unnest(ARRAY[{inner}]::bigint[]) WITH ORDINALITY AS v(value,ord))
SELECT pg_catalog.current_setting('server_version') AS server_version,
 o.value AS outer_value, ARRAY(SELECT i.value FROM inner_values i ORDER BY i.ord) AS inner_values,
 ARRAY(SELECT o.value=i.value FROM inner_values i ORDER BY i.ord) AS equality_results,
 ARRAY(SELECT o.value<>i.value FROM inner_values i ORDER BY i.ord) AS inequality_results,
 ARRAY(SELECT i.value FROM inner_values i WHERE i.value=o.value ORDER BY i.ord) AS matching_values,
 o.value NOT IN(SELECT i.value FROM inner_values i) AS not_in,
 NOT EXISTS(SELECT 1 FROM inner_values i WHERE i.value=o.value) AS not_exists
FROM outer_values o"""


def sql_and(values: list[bool | None]) -> bool | None:
    if any(value is False for value in values):
        return False
    return None if any(value is None for value in values) else True


def truth(value: bool | None) -> str:
    return "UNKNOWN" if value is None else "TRUE" if value else "FALSE"


def display(value: int | None) -> str:
    return "NULL" if value is None else str(value)


def render(row: MembershipRow, german: bool, marker: str) -> str:
    # Do not conflate FALSE with UNKNOWN; check all engine evidence before explaining.
    equalities = [
        None if row.outer_value is None or value is None else row.outer_value == value
        for value in row.inner_values
    ]
    inequalities = [None if value is None else not value for value in equalities]
    matching = [
        value for value, equal in zip(row.inner_values, equalities, strict=True) if equal is True
    ]
    if (
        row.equality_results != equalities
        or row.inequality_results != inequalities
        or row.matching_values != matching
        or row.not_in is not sql_and(inequalities)
        or row.not_exists is not (not any(value is True for value in equalities))
    ):
        raise AppError(
            "membership_evidence_invalid", "The lab returned inconsistent comparison evidence.", 502
        )
    lines = []
    for value, equal, unequal in zip(row.inner_values, equalities, inequalities, strict=True):
        lines.append(f"| {display(value)} | {truth(equal)} | {truth(unequal)} |")
    if not lines:
        lines = ["| ∅ | — | — |"]
    tests = " AND ".join(truth(value) for value in inequalities)
    keep_in, keep_exists = row.not_in is True, row.not_exists is True
    if german:
        intro = "Lokaler Vergleich mit Literalwerten. Es wurden keine Projekttabellen gelesen oder verändert."
        header = "Innerer Wert | äußerer Wert = innerer Wert | äußerer Wert <> innerer Wert"
        empty = "Die innere Menge ist leer. Es gibt keine Ungleichheitsprüfungen; das Ergebnis ist TRUE."
        conjunction = (
            f"Die Ungleichheitsprüfungen ergeben {tests} = {truth(row.not_in)}." if tests else empty
        )
        details = (
            f"**NOT IN:** {conjunction} WHERE behält nur TRUE. "
            + (
                "Die äußere Zeile bleibt erhalten."
                if keep_in
                else "Die äußere Zeile wird verworfen."
            )
            + "\n\n**NOT EXISTS:** Nur Gleichheitsprüfungen mit TRUE zählen als Treffer. "
            + f"Die Abfrage findet {len(matching)} passende innere Zeile(n). "
            + f"Das Ergebnis ist {truth(row.not_exists)}. "
            + (
                "Die äußere Zeile bleibt erhalten."
                if keep_exists
                else "Die äußere Zeile wird verworfen."
            )
        )
        scope = "Diese Erklärung gilt für die angegebenen Werte und den Gleichheitstest der korrelierten Unterabfrage."
    else:
        intro = "Local comparison of literal values. No project tables were read or changed."
        header = "Inner value | outer value = inner value | outer value <> inner value"
        empty = "The inner set is empty. There are no inequality tests; the result is TRUE."
        conjunction = (
            f"The inequality tests give {tests} = {truth(row.not_in)}." if tests else empty
        )
        details = (
            f"**NOT IN:** {conjunction} WHERE keeps only TRUE. "
            + ("The outer row is kept." if keep_in else "The outer row is removed.")
            + "\n\n**NOT EXISTS:** Only TRUE equality tests count as matches. "
            + f"The query finds {len(matching)} matching inner row(s). "
            + f"The result is {truth(row.not_exists)}. "
            + ("The outer row is kept." if keep_exists else "The outer row is removed.")
        )
        scope = "This explanation applies to the supplied values and the correlated subquery's equality test."
    metadata_header = "Eigenschaft | Beobachteter Wert" if german else "Property | Observed value"
    return (
        intro
        + f"\n\n`outer = {display(row.outer_value)}`; "
        + "`inner = ["
        + ", ".join(display(v) for v in row.inner_values)
        + "]`\n\n"
        + f"| {header} |\n| --- | --- | --- |\n"
        + "\n".join(lines)
        + "\n\n"
        + details
        + marker
        + "\n\n"
        + scope
        + f"\n\n| {metadata_header} |\n| --- | --- |\n| server_version | {row.server_version} |"
    )


async def membership_answer(text: str, state: Any, ctx: Any) -> MembershipAnswer | None:
    if state.mode != "neutral" or state.delivery != "explicit" or state.incident is not None:
        return None
    try:
        values = parse_request(text)
    except (ValidationError, ValueError):
        values = None
        if not text.casefold().startswith(
            ("run a local comparison of not in", "führe einen lokalen vergleich von not in")
        ):
            return None
        error = (
            "Bitte verwende eine ganze Zahl oder null und höchstens 20 solche innere Werte."
            if state.language == "de"
            else "Use an integer or null and at most 20 such inner values."
        )
    else:
        if values is None:
            return None
        error = ""
    from backend.tutor.tools import ToolResult, TurnBudget, dispatch

    from app.integrations.supabase_project import project_module

    module = project_module()
    messages: list[dict[str, Any]] = [{"role": "user", "content": text}]
    calls = []
    citations = []
    if values is not None and (ctx is None or ctx.lab is None):
        error = (
            "Das lokale Lab ist nicht bereit. Die Werte wurden nicht ausgeführt."
            if state.language == "de"
            else "The local lab is not ready. These values were not executed."
        )
    if not error:
        assert values is not None
        budget = TurnBudget()
        args = {"sql": comparison_sql(values), "role": "authenticated", "persist": False}
        result = await dispatch("run_lab_sql", args, ctx, budget)
        tool_id = "membership-" + str(uuid4())
        calls.append(("run_lab_sql", args, result.is_error))
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": tool_id, "name": "run_lab_sql", "input": args}
                    ],
                },
                {"role": "user", "content": [result.to_block(tool_id)]},
            ]
        )
        if result.is_error:
            raise AppError(
                "membership_execution_failed", "The local comparison did not produce a result.", 502
            )
        evidence = json.loads(result.content)
        if (
            not evidence.get("ok")
            or evidence.get("persisted")
            or len(evidence.get("rows", [])) != 1
        ):
            raise AppError(
                "membership_execution_failed", "The local comparison did not produce a result.", 502
            )
        row = MembershipRow.model_validate(evidence["rows"][0])
        if row.outer_value != values.outer or row.inner_values != values.inner:
            raise AppError(
                "membership_evidence_invalid", "The lab returned different input values.", 502
            )
        source_args = {
            "query": "PostgreSQL NOT IN NOT EXISTS NULL subquery expressions",
            "k": 8,
            "products": ["database"],
        }
        try:
            source = await dispatch("search_docs", source_args, ctx, budget)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Membership source lookup failed: %s", type(exc).__name__
            )
            source = ToolResult(
                "Documentation lookup unavailable; actual lab execution evidence is retained.",
                is_error=True,
            )
        source_id = "membership-source-" + str(uuid4())
        calls.append(("search_docs", source_args, source.is_error))
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": source_id,
                            "name": "search_docs",
                            "input": source_args,
                        }
                    ],
                },
                {"role": "user", "content": [source.to_block(source_id)]},
            ]
        )
        major = row.server_version.split(".")[0]
        for hit in json.loads(source.content).get("results", []) if not source.is_error else []:
            if (
                hit["url"].split("#")[0]
                == f"https://www.postgresql.org/docs/{major}/functions-subquery.html"
                and hit["tier"] < 4
            ):
                citations = [
                    {
                        "n": 1,
                        "url": hit["url"],
                        "title": hit["title"],
                        "tier": hit["tier"],
                        "fetched_at": hit.get("fetched_at"),
                    }
                ]
                break
        body = render(row, state.language == "de", " [1]" if citations else "")
        speech = f"NOT IN: {truth(row.not_in)}. NOT EXISTS: {truth(row.not_exists)}."
    else:
        body = error
        speech = error
    turn = module.TutorTurn(
        mode=state.mode,
        language=state.language,
        persona_on=state.persona_on,
        text=body,
        speech=speech,
        citations=citations,
    )
    messages.append({"role": "assistant", "content": body})
    return MembershipAnswer(turn, messages, calls)
