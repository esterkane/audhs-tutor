"""Validated saved-lab evidence and deterministic retry reports; no new SQL or model prose."""

import json
from dataclasses import dataclass
from typing import Any, Literal

from app.integrations.supabase_isolation_lab import IsolationInput
from app.kernel.evidence_answers import (
    Comparison,
    EvidencePlan,
    EvidenceSource,
    FactCatalog,
    PlanSlot,
    PresenceBinding,
    UnsupportedPlan,
    ValueBinding,
    assemble,
)


@dataclass(frozen=True)
class StoredExperiment:
    ordinal: int
    source: EvidenceSource
    workers: int
    minimum: int
    first_commit: str

    def descriptor(self) -> dict[str, Any]:
        return {
            "id": self.source.id,
            "ordinal": self.ordinal,
            "workers": self.workers,
            "minimum_active": self.minimum,
            "first_commit": self.first_commit,
        }


def _integer(value: Any, maximum: int) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise UnsupportedPlan("An observation has an invalid integer")
    return value


def _boolean(value: Any) -> bool:
    if type(value) is not bool:
        raise UnsupportedPlan("An observation has an invalid boolean")
    return value


def _mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise UnsupportedPlan("An observation is incomplete")
    return value


def _validate(value: Any, arguments: Any) -> dict[str, Any]:
    value = _mapping(value)
    if value.get("database") != "lab" or value.get("schema_removed") is not True:
        raise UnsupportedPlan("The local experiment and cleanup are not confirmed")
    raw_inputs = _mapping(value.get("input"))
    _integer(raw_inputs.get("workers"), 20)
    _integer(raw_inputs.get("minimum_active"), 20)
    inputs = IsolationInput.model_validate(raw_inputs).model_dump()
    declared = _mapping(arguments)
    _integer(declared.get("workers"), 20)
    _integer(declared.get("minimum_active"), 20)
    if inputs != value.get("input") or inputs != declared:
        raise UnsupportedPlan("Observed inputs do not match the recorded tool call")
    workers, minimum = inputs["workers"], inputs["minimum_active"]
    runs = value.get("runs")
    expected = [
        ("read committed", "none"),
        ("repeatable read", "none"),
        ("serializable", "none"),
        ("serializable", "full"),
        ("serializable", "update_only"),
    ]
    if not isinstance(runs, list) or len(runs) != 5:
        raise UnsupportedPlan("The complete set of independent trials is unavailable")
    for run, (level, strategy) in zip(runs, expected, strict=True):
        run = _mapping(run)
        if "retry" not in run:
            raise UnsupportedPlan("The retry observation is absent")
        if (run.get("level"), run.get("retry_strategy")) != (level, strategy):
            raise UnsupportedPlan("The trial schedule differs from the supported experiment")
        transactions = _mapping(run.get("transactions"))
        if set(transactions) != {"a", "b"}:
            raise UnsupportedPlan("The two recorded transactions are unavailable")
        committed_updates = 0
        for tx in transactions.values():
            tx = _mapping(tx)
            count = _integer(_mapping(tx.get("read")).get("count"), workers)
            if count != workers:
                raise UnsupportedPlan(
                    "The initial read differs from the fixed fresh-fixture schedule"
                )
            if _boolean(tx.get("decision")) != (count > minimum):
                raise UnsupportedPlan("The recorded row decision contradicts its predicate")
            updated = _integer(tx.get("updated"), 1)
            committed = _boolean(tx.get("committed"))
            if committed and tx.get("error") is not None:
                raise UnsupportedPlan("A committed transaction also reports an error")
            if tx.get("error") is None and updated != int(count > minimum):
                raise UnsupportedPlan("The recorded update contradicts its decision")
            committed_updates += updated if committed else 0
        retry = run.get("retry")
        if retry is not None:
            retry = _mapping(retry)
            if "read" not in retry:
                raise UnsupportedPlan("The retry read observation is absent")
            actor = retry.get("transaction")
            if strategy == "none" or actor not in {"a", "b"}:
                raise UnsupportedPlan("Unexpected retry actor or strategy")
            failed = transactions[actor]
            if failed.get("committed") or _mapping(failed.get("error")).get("sqlstate") != "40001":
                raise UnsupportedPlan("The retry has no matching serialization failure")
            read = retry.get("read")
            if strategy == "full":
                count = _integer(_mapping(read).get("count"), workers)
                if count != workers - committed_updates:
                    raise UnsupportedPlan("The fresh retry read contradicts committed changes")
            else:
                if read is not None:
                    raise UnsupportedPlan("UPDATE-only unexpectedly reports a new read")
                count = _integer(_mapping(failed.get("read")).get("count"), workers)
            if _boolean(retry.get("decision")) != (count > minimum):
                raise UnsupportedPlan("Retry decision contradicts its recorded count")
            updated = _integer(retry.get("updated"), 1)
            committed = _boolean(retry.get("committed"))
            if retry.get("error") is None and updated != int(count > minimum):
                raise UnsupportedPlan("Retry update contradicts its decision")
            if committed and retry.get("error") is not None:
                raise UnsupportedPlan("Committed retry also reports an error")
            committed_updates += updated if committed else 0
        final = _integer(run.get("final_active"), workers)
        if final != workers - committed_updates or _boolean(run.get("minimum_satisfied")) != (
            final >= minimum
        ):
            raise UnsupportedPlan("Final count contradicts committed updates or the minimum")
    return _mapping(value)


def stored_experiments(history: list[dict[str, Any]]) -> tuple[StoredExperiment, ...]:
    calls: dict[str, tuple[int, Any, int]] = {}
    duplicate: set[str] = set()
    ordinal = 0
    for position, message in enumerate(history):
        content = message.get("content")
        if message.get("role") != "assistant" or not isinstance(content, list):
            continue
        for block in content:
            if (
                not isinstance(block, dict)
                or block.get("type") != "tool_use"
                or block.get("name") != "compare_isolation_lab"
                or not isinstance(block.get("id"), str)
            ):
                continue
            identity = block["id"]
            if identity in calls:
                duplicate.add(identity)
            else:
                ordinal += 1
                calls[identity] = ordinal, block.get("input"), position
    result_counts: dict[str, int] = {}
    for message in history:
        content = message.get("content")
        if message.get("role") == "user" and isinstance(content, list):
            for block in content:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_result"
                    and isinstance(block.get("tool_use_id"), str)
                ):
                    identity = block["tool_use_id"]
                    result_counts[identity] = result_counts.get(identity, 0) + 1
    found = []
    seen: set[str] = set()
    for position, message in enumerate(history):
        content = message.get("content")
        if message.get("role") != "user" or not isinstance(content, list):
            continue
        for block in content:
            if (
                not isinstance(block, dict)
                or block.get("type") != "tool_result"
                or block.get("is_error") is not False
            ):
                continue
            identity = block.get("tool_use_id")
            if (
                not isinstance(identity, str)
                or identity not in calls
                or identity in duplicate
                or identity in seen
                or result_counts.get(identity) != 1
            ):
                continue
            seen.add(identity)
            index, args, call_position = calls[identity]
            if position <= call_position:
                continue
            try:
                value = _validate(json.loads(block["content"]), args)
                initial = EvidenceSource.capture("candidate", "observed_tool_result", value)
                source = EvidenceSource.capture(
                    f"experiment{index}-{initial.revision[:12]}", "observed_tool_result", value
                )
            except (ValueError, TypeError, KeyError):
                continue
            inputs = value["input"]
            found.append(
                StoredExperiment(
                    index,
                    source,
                    inputs["workers"],
                    inputs["minimum_active"],
                    inputs["first_commit"],
                )
            )
    return tuple(sorted(found, key=lambda item: item.ordinal))


def retry_report(
    experiments: tuple[StoredExperiment, ...],
    record_ids: list[str],
    *,
    language: Literal["en", "de"],
    explain_decision: bool = False,
) -> str:
    if not record_ids or len(record_ids) > 4 or len(set(record_ids)) != len(record_ids):
        raise UnsupportedPlan("Select one to four distinct recorded experiments")
    lookup = {e.source.id: e for e in experiments}
    if any(identity not in lookup for identity in record_ids):
        raise UnsupportedPlan("A selected experiment is outside this session's evidence")
    reports = []
    german = language == "de"

    def yes_no(value: Any) -> str:
        return ("ja" if value else "nein") if german else ("yes" if value else "no")

    for identity in record_ids:
        item = lookup[identity]
        value = json.loads(item.source.canonical_json)
        if explain_decision and any(value["runs"][index].get("retry") is None for index in (3, 4)):
            raise UnsupportedPlan("A causal retry comparison requires both observed retries")
        bindings: list[ValueBinding | PresenceBinding] = [
            ValueBinding("minimum", identity, "/input/minimum_active")
        ]
        comparisons = []
        labels = {}
        contract = {}
        for index, strategy in [(3, "full"), (4, "update_only")]:
            prefix = "full" if strategy == "full" else "only"
            base = f"/runs/{index}"
            run = value["runs"][index]
            retry = run.get("retry")
            specs = {
                "performed": (
                    PresenceBinding,
                    base + "/retry",
                    ("Retry performed", "Retry ausgeführt"),
                ),
                "final": (
                    ValueBinding,
                    base + "/final_active",
                    ("Active rows afterwards", "Aktive Zeilen danach"),
                ),
            }
            specs["minimum_met"] = (
                ValueBinding,
                base + "/minimum_satisfied",
                ("Final minimum rule met", "Mindestregel am Ende erfüllt"),
            )
            if retry is not None:
                actor = retry["transaction"]
                count_path = (
                    base + "/retry/read/count"
                    if strategy == "full"
                    else base + f"/transactions/{actor}/read/count"
                )
                specs.update(
                    {
                        "count": (
                            ValueBinding,
                            count_path,
                            (
                                "Newly read active count"
                                if strategy == "full"
                                else "Original count reused",
                                "Neu gelesene aktive Anzahl"
                                if strategy == "full"
                                else "Übernommene ursprüngliche Anzahl",
                            ),
                        ),
                        "new_read": (
                            PresenceBinding,
                            base + "/retry/read",
                            ("New read performed", "Neu gelesen"),
                        ),
                        "decision": (
                            ValueBinding,
                            base + "/retry/decision",
                            ("Decided to deactivate own row", "Eigene Zeile deaktivieren"),
                        ),
                        "updated": (
                            ValueBinding,
                            base + "/retry/updated",
                            ("Rows affected before commit", "Betroffene Zeilen vor Commit"),
                        ),
                        "committed": (
                            ValueBinding,
                            base + "/retry/committed",
                            ("Commit succeeded", "Commit erfolgreich"),
                        ),
                    }
                )
                comparisons.append(
                    Comparison(prefix + ".condition", prefix + ".count", "minimum", "gt")
                )
                contract[prefix + ".condition"] = frozenset({prefix + ".condition"})
                labels[prefix + ".condition"] = (
                    "Deactivation condition (count > minimum)",
                    "Bedingung zum Deaktivieren (Anzahl > Minimum)",
                )
            if retry is None:
                for actor in ("a", "b"):
                    specs["initial_count_" + actor] = (
                        ValueBinding,
                        base + f"/transactions/{actor}/read/count",
                        ("Original count", "Ursprüngliche Anzahl"),
                    )
                    specs["initial_commit_" + actor] = (
                        ValueBinding,
                        base + f"/transactions/{actor}/committed",
                        ("Original commit", "Ursprünglicher Commit"),
                    )
                    comparisons.append(
                        Comparison(
                            prefix + ".initial_condition_" + actor,
                            prefix + ".initial_count_" + actor,
                            "minimum",
                            "gt",
                        )
                    )
                    contract[prefix + ".initial_condition_" + actor] = frozenset(
                        {prefix + ".initial_condition_" + actor}
                    )
                    labels[prefix + ".initial_condition_" + actor] = (
                        "Original update condition",
                        "Ursprüngliche Update-Bedingung",
                    )
            for name, (kind, pointer, label) in specs.items():
                fact_id = prefix + "." + name
                bindings.append(kind(fact_id, identity, pointer))
                contract[fact_id] = frozenset({fact_id})
                labels[fact_id] = (
                    ("Full retry: " if prefix == "full" else "UPDATE-only: ") + label[0],
                    ("Vollständiger Retry: " if prefix == "full" else "Nur UPDATE: ") + label[1],
                )
        catalog = FactCatalog.build([item.source], bindings, comparisons)
        plan = EvidencePlan(
            catalog_digest=catalog.digest,
            slots=[
                PlanSlot(slot=slot, fact_id=next(iter(allowed)))
                for slot, allowed in contract.items()
            ],
        )
        facts = dict(assemble(plan, catalog, contract))
        paragraphs = []
        for prefix, name in [
            ("full", "Vollständiger Retry" if german else "Full retry"),
            ("only", "Nur UPDATE erneut" if german else "UPDATE-only retry"),
        ]:
            final = facts[prefix + ".final"].value
            if not facts[prefix + ".performed"].value:
                initial = "; ".join(
                    f"{actor.upper()}: {facts[prefix + '.initial_condition_' + actor].expression}, "
                    + ("Commit: " if german else "commit: ")
                    + yes_no(facts[prefix + ".initial_commit_" + actor].value)
                    for actor in ("a", "b")
                )
                minimum_met = yes_no(facts[prefix + ".minimum_met"].value)
                paragraphs.append(
                    f"**{name}:** "
                    + (
                        (
                            f"nicht ausgeführt; danach {final} aktive Zeilen. "
                            f"Ursprüngliche Versuche: {initial}. Mindestregel erfüllt: {minimum_met}."
                        )
                        if german
                        else (
                            f"not performed; {final} active rows afterwards. "
                            f"Original attempts: {initial}. Final minimum rule met: {minimum_met}."
                        )
                    )
                )
                continue
            count = facts[prefix + ".count"].value
            condition = facts[prefix + ".condition"].expression
            new_read = facts[prefix + ".new_read"].value
            decision = facts[prefix + ".decision"].value
            updated = facts[prefix + ".updated"].value
            committed = facts[prefix + ".committed"].value
            if german:
                reading = (
                    f"neu gelesen: {count}"
                    if new_read
                    else f"nicht neu gelesen; ursprüngliche Anzahl {count} übernommen"
                )
                action = (
                    "eigene Zeile deaktivieren" if decision else "eigene Zeile nicht deaktivieren"
                )
                paragraph = (
                    f"**{name}:** {reading}. `{condition}`. Entscheidung: {action}; betroffene "
                    f"Zeilen vor Commit: {updated}. Commit erfolgreich: {yes_no(committed)}. "
                    f"Danach aktiv: {final}."
                )
            else:
                reading = (
                    f"newly read count: {count}"
                    if new_read
                    else f"no new read; reused original count {count}"
                )
                action = "deactivate own row" if decision else "do not deactivate own row"
                paragraph = (
                    f"**{name}:** {reading}. `{condition}`. Decision: {action}; rows affected "
                    f"before commit: {updated}. Commit succeeded: {yes_no(committed)}. Active "
                    f"afterwards: {final}."
                )
            if explain_decision:
                if german:
                    paragraph = (
                        f"**{name}:** {reading}. Die Bedingung ist `{condition}`; deshalb "
                        f"lautete die Entscheidung: {action}. Betroffene Zeilen vor Commit: "
                        f"{updated}; Commit erfolgreich: {yes_no(committed)}. Danach aktiv: {final}."
                    )
                else:
                    paragraph = (
                        f"**{name}:** {reading}. The condition is `{condition}`, so the "
                        f"decision was: {action}. Rows affected before commit: {updated}; "
                        f"commit succeeded: {yes_no(committed)}. Active afterwards: {final}."
                    )
            minimum_met = yes_no(facts[prefix + ".minimum_met"].value)
            paragraph += (
                f" Mindestregel am Ende erfüllt: {minimum_met}."
                if german
                else f" Final minimum rule met: {minimum_met}."
            )
            paragraphs.append(paragraph)
        title = (
            f"Gespeicherter Versuch {item.ordinal}"
            if german
            else f"Saved experiment {item.ordinal}"
        )
        header = (
            (
                f"{title}: Startanzahl {item.workers}, Minimum {item.minimum}, erster "
                f"Commit-Versuch {item.first_commit.upper()}"
            )
            if german
            else (
                f"{title}: {item.workers} initially active, minimum {item.minimum}, first "
                f"commit attempt {item.first_commit.upper()}"
            )
        )
        source = (
            "Quelle: gespeicherter lokaler Versuch" if german else "Source: saved local experiment"
        ) + f" `{identity}` · `{item.source.revision[:12]}`"
        reports.append("**" + header + "**\n\n" + "\n\n".join(paragraphs) + "\n\n" + source)
    intro = (
        (
            "Die Entscheidung zum Deaktivieren prüft `Anzahl > Minimum`; die "
            "Mindestregel am Ende prüft `aktiv >= Minimum`. Der Commit ist ein separates "
            "Ergebnis. Es wurde kein Versuch erneut ausgeführt."
        )
        if language == "de"
        else (
            "The deactivation decision tests `count > minimum`; the final minimum rule "
            "tests `active >= minimum`. Commit is a separate outcome. No new SQL was "
            "executed."
        )
    )
    return intro + "\n\n" + "\n\n---\n\n".join(reports)
