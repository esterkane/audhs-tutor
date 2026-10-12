#!/usr/bin/env python3
"""Offline-only synthetic trial preflight; never reads keys or makes model calls."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

MODEL = "meta/muse-glimmer-30b"
PROVIDER = "deepinfra/bf16"
ARTIFACT_SHA256 = "7badcd9ff079f540a59a07d650e583ea6b9f209156ff72f497ab0df19b296961"
CONTEXT_LIMIT = 131072
OUTPUT_LIMIT = 900
# Verified 2026-10-12; execution must revalidate pricing/capabilities before calls.
INPUT_RATE = Decimal("0.0000003")
OUTPUT_RATE = Decimal("0.0000012")
FEE_MULTIPLIER = Decimal("1.055")
CEILING = Decimal(1)


def reservation() -> Decimal:
    """Charge the entire advertised context as input; no speculative cache savings."""
    return (CONTEXT_LIMIT * INPUT_RATE + OUTPUT_LIMIT * OUTPUT_RATE) * FEE_MULTIPLIER


class CampaignBudget:
    """Sequential campaign accounting. Unknown billing halts further reservations."""

    def __init__(self, ceiling: Decimal = CEILING):
        if not ceiling.is_finite() or not Decimal(0) < ceiling <= CEILING:
            raise ValueError("Ceiling must be positive and at most the approved $1")
        self.ceiling = ceiling
        self.charged = Decimal(0)
        self.pending = False
        self.halted = False

    def reserve(self) -> Decimal:
        if self.halted or self.pending:
            raise ValueError("Unsettled or halted campaign")
        amount = reservation()
        if self.charged + amount > self.ceiling:
            raise ValueError("Insufficient budget for worst-case request")
        self.charged += amount
        self.pending = True
        return amount

    def settle(self, provider_cost: Decimal | None) -> None:
        if not self.pending:
            raise ValueError("No outstanding reservation")
        self.pending = False
        if provider_cost is None or not provider_cost.is_finite() or provider_cost < 0:
            self.halted = True
            return  # retain the reservation; unknown billing is never free
        actual = provider_cost * FEE_MULTIPLIER
        if actual > reservation():
            self.halted = True
        self.charged += actual - reservation()


def load_requests(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ARTIFACT_SHA256:
        raise ValueError("Only the reviewed, frozen synthetic artifact is accepted")
    report = json.loads(raw)
    if report["synthetic"] is not True or len(report["results"]) != 8:
        raise ValueError("Expected eight synthetic cases")
    requests = []
    for case in report["results"]:
        recorded = case["gateway_requests"]
        if len(recorded) != 1 or recorded[0]["structured_schema_requested"]:
            raise ValueError("Expected one plain-text request per case")
        messages = recorded[0]["messages"]
        digest = hashlib.sha256(
            json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        if digest != recorded[0]["messages_sha256"]:
            raise ValueError("Prompt hash mismatch")
        requests.append({
            "case": case["case"],
            "messages_sha256": digest,
            "body": {
                "model": MODEL,
                "messages": messages,
                "max_tokens": OUTPUT_LIMIT,
                "temperature": 0,
                "stream": True,
                "provider": {
                    "only": [PROVIDER],
                    "allow_fallbacks": False,
                    "require_parameters": True,
                },
            },
        })
    return requests


def main() -> None:
    source = Path(__file__).resolve().parents[1] / (
        "evals/results/teaching-glimmer-fixed-20261012.json"
    )
    requests = load_requests(source)
    worst_total = reservation() * len(requests)
    if worst_total > CEILING:
        raise ValueError("Eight requests exceed approved ceiling")
    print(json.dumps({
        "mode": "offline_preflight_only",
        "cases": len(requests),
        "model": MODEL,
        "provider": PROVIDER,
        "artifact_sha256": ARTIFACT_SHA256,
        "reservation_per_request_usd": str(reservation()),
        "eight_request_bound_usd": str(worst_total),
        "approved_ceiling_usd": str(CEILING),
        "paid_calls": 0,
        "execution_ready": False,
        "remaining": "credential, live price/cap revalidation, streaming adapter and review",
    }, indent=2))


if __name__ == "__main__":
    main()
