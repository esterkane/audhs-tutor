"""Explicit local isolation experiments: measured evidence, deterministic bilingual reading."""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.integrations.supabase_isolation_lab import (
    IsolationInput,
    IsolationLabError,
    run_isolation_experiment,
)


@dataclass(frozen=True)
class IsolationAnswer:
    turn: Any
    messages: list[dict[str, Any]]
    calls: list[tuple[str, dict[str, Any], bool]]


def parse_request(text: str) -> IsolationInput | None:
    if len(text) > 1000:
        return None
    patterns = (
        r"Compare transaction isolation locally for (-?\d+) active workers, minimum (-?\d+),"
        r" attempting ([AB])'s commit first\.",
        r"Vergleiche Transaktionsisolation lokal mit (-?\d+) aktiven Kräften, mindestens (-?\d+),"
        r" und Commit-Versuch ([AB]) zuerst\.",
    )
    for pattern in patterns:
        if match := re.fullmatch(pattern, text.strip(), re.IGNORECASE):
            return IsolationInput.model_validate(
                {
                    "workers": int(match[1]),
                    "minimum_active": int(match[2]),
                    "first_commit": match[3].lower(),
                }
            )
    return None


def render(
    evidence: dict[str, Any], german: bool, isolation_marker: str = "", retry_marker: str = ""
) -> str:
    values = IsolationInput.model_validate(evidence["input"])
    if (
        evidence.get("database") != "lab"
        or evidence.get("schema_removed") is not True
        or len(evidence.get("runs", [])) != 5
    ):
        raise IsolationLabError("The complete local experiment was not confirmed")
    rc, rr, serial, full, only = evidence["runs"]
    expected = [
        ("read committed", "none"),
        ("repeatable read", "none"),
        ("serializable", "none"),
        ("serializable", "full"),
        ("serializable", "update_only"),
    ]
    if [(r["level"], r["retry_strategy"]) for r in evidence["runs"]] != expected:
        raise IsolationLabError("The experiment returned different transaction schedules")
    yes, no = ("ja", "nein") if german else ("yes", "no")

    def outcome(transaction: dict[str, Any]) -> str:
        if transaction["committed"]:
            return "Commit" if german else "Committed"
        error = transaction["error"] or {}
        return f"{error.get('sqlstate', '—')} ({error.get('stage', '—')})"

    header = (
        "Isolation | A | B | Aktiv danach | Mindestregel erfüllt"
        if german
        else "Isolation | A | B | Active afterwards | Minimum satisfied"
    )
    rows = [
        f"| {r['level']} | {outcome(r['transactions']['a'])}"
        f" | {outcome(r['transactions']['b'])} | {r['final_active']} | {yes if r['minimum_satisfied'] else no} |"
        for r in (rc, rr, serial)
    ]
    prefix = (
        f"**Gemessen im lokalen Lab (PostgreSQL {evidence['server_version']}).** "
        f"Jeder Versuch startet neu mit {values.workers} aktiven Zeilen. A und B lesen beide vor dem ersten Schreiben. "
        f"Eine Transaktion deaktiviert ihre eigene, andere Zeile "
        f"nur, wenn ihre gelesene Anzahl größer als {values.minimum_active} ist. "
        f"Commit-Versuche: {values.first_commit.upper()} zuerst. "
        f"Die Ergebnisse betreffen diese Reihenfolge, nicht dein Projekt."
        if german
        else f"**Measured in the local lab (PostgreSQL {evidence['server_version']}).** "
        f"Each trial starts afresh with {values.workers} active rows. A and B both read before either writes. "
        f"A transaction deactivates its own, different row only when its recorded count "
        f"is greater than {values.minimum_active}. "
        f"Commit attempts: {values.first_commit.upper()} first. These results describe this schedule, not your project."
    )
    rr_reads = rr["transactions"]
    update_note = (
        (
            "Die beiden Updates betreffen verschiedene Zeilen. "
            if german
            else "The updates target different rows. "
        )
        if any(t["updated"] for t in rr_reads.values())
        else (
            "Keine gelesene Anzahl überschritt das Minimum; daher wurde kein UPDATE gesendet. "
            if german
            else "Neither count exceeded the minimum, so no UPDATE was sent. "
        )
    )
    mechanism = (
        f"**Gelesene Werte:** A las {rr_reads['a']['read']['count']}, B las {rr_reads['b']['read']['count']}. "
        "Die Entscheidung beruht auf diesen früheren Anzahlen; vor dem UPDATE wird nicht erneut gezählt. "
        f"{update_note}"
        f"Bei Repeatable Read waren {sum(t['committed'] for t in rr_reads.values())} Commits erfolgreich; "
        f"danach waren {rr['final_active']} Zeilen aktiv. "
        "Gleiche gelesene Werte sind kein Beleg dafür, dass zwei Transaktionen einen gemeinsamen Snapshot besitzen."
        if german
        else f"**Read decisions:** A read {rr_reads['a']['read']['count']}; B read {rr_reads['b']['read']['count']}. "
        "Each decision uses those earlier counts; this script does not count again before the UPDATE. "
        f"{update_note}"
        f"Under Repeatable Read, {sum(t['committed'] for t in rr_reads.values())} commits succeeded; "
        f"{rr['final_active']} rows remained active. "
        "Equal observed values do not establish that two transactions share one snapshot."
    )
    failures = [
        (name.upper(), t["error"]) for name, t in serial["transactions"].items() if t["error"]
    ]
    if failures:
        observed_errors = "; ".join(
            f"{name}: {error['sqlstate']} ({error['stage']})" for name, error in failures
        )
        mechanism += (
            f" Bei Serializable wurde tatsächlich {observed_errors} beobachtet. "
            "Beide Transaktionen hatten den Zustand gelesen, den die jeweils andere ändern wollte. "
            "Für beide ursprünglichen Entscheidungen wäre A vor B und zugleich B vor A nötig: "
            "Jede Zählung muss vor der jeweils anderen Änderung liegen. "
            "Dieses Ergebnis zeigt eine abgewiesene gleichzeitige Ausführung; "
            "es bedeutet nicht, dass Serializable jede Zeilenänderung verhindert."
            if german
            else f" Serializable actually reported {observed_errors}. "
            "Each transaction had read state that the other attempted to change. "
            "Committing both original decisions would require A before B and B before A: "
            "each count must precede the other transaction's change. "
            "This is an observed rejection of that concurrent execution, "
            "not a rule that Serializable prevents every row change."
        )
    else:
        mechanism += (
            " Bei Serializable trat hier kein Transaktionsfehler auf."
            if german
            else " No transaction error occurred under Serializable in this trial."
        )
    retry_header = (
        "Neuer Serializable-Versuch | Neue Anzahl gelesen | Aktiv danach | Mindestregel erfüllt"
        if german
        else "Fresh Serializable trial | Count read on retry | Active afterwards | Minimum satisfied"
    )
    retry_rows = []
    for run, label in (
        (full, "Vollständiger Retry" if german else "Full retry"),
        (only, "Nur UPDATE erneut" if german else "UPDATE-only retry"),
    ):
        retry = run["retry"]
        count = (
            str(retry["read"]["count"])
            if retry and retry["read"]
            else ("nicht erneut gelesen" if german else "not read again")
        )
        if retry is None:
            failed = any(t["error"] for t in run["transactions"].values())
            count = (
                ("nicht ausgeführt" if german else "not performed")
                if failed
                else ("kein Retry nötig" if german else "no retry needed")
            )
        retry_rows.append(
            f"| {label} | {count} | {run['final_active']} | {yes if run['minimum_satisfied'] else no} |"
        )
    retry_note = (
        "**Vollständiger Retry:** Der vollständige Retry liest neu und trifft die Entscheidung erneut. "
        "Der UPDATE-only-Versuch übernimmt dagegen die alte Entscheidung. "
        "Die Tabelle zeigt die jeweils tatsächlich verbleibenden aktiven Zeilen. "
        "Die beiden Retry-Varianten sind getrennte, neu aufgebaute Versuche; "
        "sie laufen nicht nacheinander auf demselben Endzustand."
        if german
        else "**Full-transaction retry:** The full retry reads again and makes the decision again. "
        "The UPDATE-only trial instead reuses the old decision. "
        "The table shows the actual remaining active rows. "
        "The retry variants are separate trials with fresh fixtures, not consecutive retries on one final state."
    )
    if full["retry"] is None:
        retry_note = (
            "Hier war kein Retry nötig: Es wurde keine Transaktion mit 40001 abgewiesen. "
            "Die Retry-Varianten haben daher keinen zusätzlichen Schreibschritt ausgeführt."
            if german
            else "No retry was needed: no transaction was rejected with 40001. "
            "The retry variants therefore performed no additional write."
        )
    if full["retry"] is None and any(t["error"] for t in full["transactions"].values()):
        retry_note = (
            "Dieser Versuch hat keinen Retry ausgeführt. Die aufgezeichneten Fehler zeigen "
            "daher kein vollständiges Retry-Ergebnis."
            if german
            else "This trial did not execute a retry. Its recorded errors do not establish a full-retry outcome."
        )
    if full["retry"] is not None and full["retry"]["read"] is not None:
        fresh = full["retry"]["read"]["count"]
        decision = full["retry"]["decision"]
        if german:
            retry_note += (
                f" Der vollständige Retry prüft neu: {fresh} > {values.minimum_active} ist "
                f"{'wahr' if decision else 'falsch'}. "
                f"Er sendet daher {'ein' if decision else 'kein'} UPDATE. "
                "Der UPDATE-only-Retry übernimmt die frühere Entscheidung ohne neue Zählung. "
                f"Seine Endanzahl {only['final_active']} erfüllt das Minimum "
                f"{values.minimum_active} {'noch' if only['minimum_satisfied'] else 'nicht'}."
            )
        else:
            retry_note += (
                f" The full retry checks afresh: {fresh} > {values.minimum_active} is "
                f"{'true' if decision else 'false'}, so it {'sends' if decision else 'does not send'} an UPDATE. "
                "The UPDATE-only retry reuses the earlier decision without counting again. "
                f"Its final count {only['final_active']} "
                f"{'satisfies' if only['minimum_satisfied'] else 'violates'} the minimum {values.minimum_active}."
            )
    scope = (
        "Alle Transaktionen liefen als authenticated auf ausschließlich für diese Versuche angelegten Tabellen. "
        "Die Testtabellen wurden entfernt. "
        "Bestehende Projekttabellen und bewertete Lernfortschritte wurden nicht verändert. "
        "Die Mindestregel entscheidet nicht allein über Serialisierbarkeit: "
        "Auch wenn eine Endanzahl die Regel erfüllt, "
        "können die gelesenen Werte und Schreibabhängigkeiten einen Serialisierungsfehler auslösen."
        if german
        else "Transactions ran as authenticated on tables created solely for these trials; the fixtures were removed. "
        "Existing project tables and assessed mastery were left unchanged. "
        "The minimum rule alone does not determine serializability: "
        "an acceptable final count can still coexist with reads "
        "and write dependencies that cause a serialization failure."
    )
    return (
        prefix
        + f"\n\n| {header} |\n| --- | --- | --- | --- | --- |\n"
        + "\n".join(rows)
        + "\n\n"
        + mechanism
        + isolation_marker
        + f"\n\n| {retry_header} |\n| --- | --- | --- | --- |\n"
        + "\n".join(retry_rows)
        + "\n\n"
        + retry_note
        + retry_marker
        + "\n\n"
        + scope
        + isolation_marker
    )


async def isolation_answer(text: str, state: Any, ctx: Any) -> IsolationAnswer | None:
    if state.mode != "neutral" or state.delivery != "explicit" or state.incident is not None:
        return None
    try:
        values = parse_request(text)
    except ValidationError:
        values = None
        error = (
            "Verwende 2–20 aktive Zeilen, ein Minimum von 0 bis zur Startanzahl und A oder B zuerst."
            if state.language == "de"
            else "Use 2–20 active rows, a minimum from zero to the starting count, and A or B first."
        )
    else:
        if values is None:
            return None
        error = ""
    from app.integrations.supabase_project import project_module

    module = project_module()
    from backend.tutor.tools import ToolResult, TurnBudget, dispatch

    messages: list[dict[str, Any]] = [{"role": "user", "content": text}]
    calls = []
    citations: list[dict[str, Any]] = []
    evidence: dict[str, Any] | None = None
    if not error:
        assert values is not None
        lab_url = getattr(getattr(ctx, "lab", None), "lab_url", None)
        args = values.model_dump()
        tool_id = "isolation-" + str(uuid4())
        evidence = None
        try:
            if not isinstance(lab_url, str):
                raise IsolationLabError("The local disposable lab is not ready")
            evidence = await run_isolation_experiment(lab_url, values)
            if (
                evidence.get("input") != values.model_dump()
                or evidence.get("schema_removed") is not True
            ):
                raise IsolationLabError(
                    "The experiment did not confirm the requested inputs and cleanup"
                )
            result = ToolResult(json.dumps(evidence, ensure_ascii=False))
        except IsolationLabError as exc:
            evidence = None
            logging.getLogger(__name__).warning("Local isolation experiment failed: %s", str(exc))
            error = (
                "Das lokale Experiment konnte nicht vollständig bestätigt werden. "
                "Es wurden keine Ergebnisse übernommen."
                if state.language == "de"
                else "The local experiment could not be fully confirmed. No outcomes were accepted."
            )
            result = ToolResult(error, is_error=True)
        calls.append(("compare_isolation_lab", args, result.is_error))
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": "compare_isolation_lab",
                            "input": args,
                        }
                    ],
                },
                {"role": "user", "content": [result.to_block(tool_id)]},
            ]
        )
        if evidence is not None:
            source_args = {
                "query": "PostgreSQL transaction isolation Repeatable Read Serializable full transaction retry",
                "products": ["database"],
                "k": 8,
            }
            try:
                source = await dispatch("search_docs", source_args, ctx, TurnBudget())
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Isolation source lookup failed: %s", type(exc).__name__
                )
                source = ToolResult(
                    "Documentation unavailable; measured results are retained.", is_error=True
                )
            source_id = "isolation-source-" + str(uuid4())
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
            major = re.match(r"\d+", evidence["server_version"])
            markers = {}
            for page in ("transaction-iso.html", "mvcc-serialization-failure-handling.html"):
                for hit in (
                    json.loads(source.content).get("results", []) if not source.is_error else []
                ):
                    if (
                        major
                        and hit["url"].split("#")[0]
                        == f"https://www.postgresql.org/docs/{major[0]}/{page}"
                        and hit["tier"] < 4
                    ):
                        number = len(citations) + 1
                        citations.append(
                            {
                                "n": number,
                                "url": hit["url"],
                                "title": hit["title"],
                                "tier": hit["tier"],
                                "fetched_at": hit.get("fetched_at"),
                            }
                        )
                        markers[page] = f" [{number}]"
                        break
            body = render(
                evidence,
                state.language == "de",
                markers.get("transaction-iso.html", ""),
                markers.get("mvcc-serialization-failure-handling.html", ""),
            )
    if error:
        body = error
    speech = error
    if evidence is not None:
        labels = [
            "Read Committed",
            "Repeatable Read",
            "Serializable",
            "vollständiger Retry" if state.language == "de" else "full retry",
            "UPDATE-only Retry" if state.language == "de" else "UPDATE-only retry",
        ]
        unit = "aktiv" if state.language == "de" else "active"
        speech = (
            ("Lokales Lab: " if state.language == "de" else "Local lab: ")
            + "; ".join(
                f"{label}: {run['final_active']} {unit}"
                for label, run in zip(labels, evidence["runs"], strict=True)
            )
            + "."
        )
        codes = sorted(
            {
                t["error"]["sqlstate"]
                for t in evidence["runs"][2]["transactions"].values()
                if t["error"]
            }
        )
        if codes:
            speech += " SQLSTATE: " + ", ".join(codes) + "."
    turn = module.TutorTurn(
        mode=state.mode,
        language=state.language,
        persona_on=state.persona_on,
        text=body,
        speech=speech,
        citations=citations,
    )
    messages.append({"role": "assistant", "content": body})
    return IsolationAnswer(turn, messages, calls)
