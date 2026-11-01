"""Deterministic presentation of assembled evidence; no model-authored factual prose."""

import json
import re
from collections.abc import Mapping
from typing import Literal

from app.kernel.evidence_answers import EvidenceFact, UnsupportedPlan


def _literal(value: str) -> str:
    fence = "`" * (max((len(m[0]) for m in re.finditer(r"`+", value)), default=0) + 1)
    if "\n" in value or "\r" in value:
        fence = "`" * max(3, len(fence))
        return f"\n{fence}text\n{value}\n{fence}\n"
    return f"{fence} {value} {fence}"


def render_evidence(
    answer: tuple[tuple[str, EvidenceFact], ...],
    labels: Mapping[str, tuple[str, str]],
    *,
    language: Literal["en", "de"],
) -> str:
    """Labels are host-authored (English/German), never model-generated assertions.

    Keep derived proof, copied values and attributed unverified statements distinguishable.
    Missing labels or oversized answers fail before delivery instead of silently cutting text.
    """
    german = language == "de"
    kinds = {
        "observed_tool_result": "Beobachtung" if german else "observation",
        "accepted_material": "angenommenes Material" if german else "accepted material",
        "learner_statement": "Lernendenaussage, ungeprüft"
        if german
        else "learner statement, unverified",
        "tutor_claim": "Tutoraussage, ungeprüft" if german else "tutor statement, unverified",
    }
    parts = []
    for slot, fact in answer:
        if not fact.references:
            raise UnsupportedPlan("An evidence answer requires original source references")
        if slot not in labels:
            raise UnsupportedPlan("An answer slot has no host-authored label")
        label = labels[slot][1 if german else 0]
        if fact.value is None:
            value = "null"
        elif type(fact.value) is bool:
            value = ("ja" if fact.value else "nein") if german else ("yes" if fact.value else "no")
        elif isinstance(fact.value, str):
            value = fact.value
        else:
            value = json.dumps(fact.value, allow_nan=False)
        parts.append(f"**{_literal(label)}:** {_literal(value)}")
        if fact.expression is not None:
            parts.append(
                ("Berechnet aus den Quellenwerten: " if german else "Computed from source values: ")
                + _literal(fact.expression)
            )
        origins = "; ".join(
            dict.fromkeys(
                f"{kinds[r.kind]} · {r.source_id} · {r.revision[:12]} · {r.pointer or '/'}"
                for r in fact.references
            )
        )
        parts.append(("Quelle: " if german else "Source: ") + _literal(origins))
    text = "\n\n".join(parts)
    if not text or len(text) > 64000:
        raise UnsupportedPlan("The complete evidence answer exceeds the presentation bound")
    return text
