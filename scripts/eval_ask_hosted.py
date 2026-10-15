#!/usr/bin/env python3
"""Frozen synthetic Ask comparison. Defaults to offline preflight, never inference."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.schemas.answer_checks import AnswerReviewProposal
from eval_hosted_glimmer import API, stream_reply, validate_catalog
from glimmer_trial_preflight import FEE_MULTIPLIER, MODEL, reservation

DIGEST = "24bd2a619d741c1a176c45706b86046d9f22e4c207bdf4f986a9c8734be3491d"
SOURCE = ROOT / "evals/cases/ask-hosted-campaign.json"
JOURNAL = ROOT / "data/evals/ask-hosted-20261015.sqlite3"
CEILING = Decimal("0.32")


def load_campaign(path: Path = SOURCE) -> dict[str, Any]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DIGEST:
        raise ValueError("Frozen campaign changed")
    campaign: dict[str, Any] = json.loads(raw)
    if len(campaign["cases"]) != 5 or reservation() * 5 > CEILING:
        raise ValueError("Campaign exceeds allowance")
    for case in campaign["cases"]:
        body = case["request_body"]
        if case["kind"] == "source_review" and (
            body["response_format"]["json_schema"]["schema"]
            != AnswerReviewProposal.model_json_schema()
        ):
            raise ValueError("Review schema changed; renew experiment before execution")
    return campaign


class Journal:
    def __init__(self, path: Path, campaign: dict[str, Any]):
        self.names = {case["id"] for case in campaign["cases"]}
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=5)
        self.db.execute("PRAGMA synchronous=FULL")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS campaign (identity TEXT PRIMARY KEY)"
            )
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS attempts (name TEXT PRIMARY KEY, state TEXT, charge TEXT, result TEXT)"
            )
            identity = DIGEST + ":" + str(CEILING) + ":" + str(reservation())
            existing = self.db.execute("SELECT identity FROM campaign").fetchall()
            if existing and existing != [(identity,)]:
                raise ValueError("Journal belongs to a different campaign")
            if not existing:
                self.db.execute("INSERT INTO campaign VALUES (?)", (identity,))

    def reserve(self, name: str) -> bool:
        if name not in self.names:
            raise ValueError("Unknown case")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            rows = self.db.execute("SELECT name,state,charge FROM attempts").fetchall()
            if any(state != "settled" for _, state, _ in rows):
                raise ValueError("Uncertain prior attempt; no automatic resend")
            if any(prior == name for prior, _, _ in rows):
                return False
            total = sum((Decimal(charge) for _, _, charge in rows), Decimal(0))
            if len(rows) >= 5 or total + reservation() > CEILING:
                raise ValueError("Allowance exhausted")
            self.db.execute(
                "INSERT INTO attempts VALUES (?, 'pending', ?, NULL)",
                (name, str(reservation())),
            )
        return True

    def settle(self, name: str, result: dict[str, Any]) -> None:
        state, charge = "halted", reservation()
        try:
            actual = Decimal(str(result.get("cost_usd"))) * FEE_MULTIPLIER
            if actual.is_finite() and actual >= 0:
                charge = max(charge, actual)
                if result.get("accounting_valid") is True and actual <= reservation():
                    state, charge = "settled", actual
        except ArithmeticError:
            pass
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute(
                "UPDATE attempts SET state=?,charge=?,result=? WHERE name=? AND state='pending'",
                (state, str(charge), json.dumps(result), name),
            )
            if row.rowcount != 1:
                raise ValueError("No pending attempt")

    def report(self) -> dict[str, Any]:
        rows = self.db.execute(
            "SELECT name,state,charge,result FROM attempts ORDER BY rowid"
        ).fetchall()
        return {
            "campaign_sha256": DIGEST,
            "ceiling_usd": str(CEILING),
            "results": [
                {
                    "case": name,
                    "state": state,
                    "reserved_or_charged_usd": charge,
                    "result": json.loads(result) if result else None,
                }
                for name, state, charge, result in rows
            ],
        }


def check_review(case: dict[str, Any], result: dict[str, Any]) -> None:
    if case["kind"] != "source_review":
        return
    result["first_json_seconds"] = result.pop("first_visible_seconds", None)
    result["target_claim_coverage"] = "requires_human_review"
    try:
        proposal = AnswerReviewProposal.model_validate_json(result["text"])
        source_message = case["messages"][2]["content"]
        passages = json.loads(
            source_message.removeprefix("<source_passages>\n").removesuffix(
                "\n</source_passages>"
            )
        )
        seen: set[str] = set()
        for claim in proposal.claims:
            if claim.claim_quote not in case["answer"] or claim.claim_quote in seen:
                raise ValueError("Invalid claim quotation")
            seen.add(claim.claim_quote)
            for evidence in claim.evidence:
                if (
                    evidence.passage_id not in passages
                    or evidence.quote not in passages[evidence.passage_id]
                ):
                    raise ValueError("Invalid evidence quotation")
        result["schema_and_quote_binding"] = "passed_not_semantic_verification"
    except (ValueError, KeyError, TypeError):
        result["schema_and_quote_binding"] = "failed"
        result["status"] = "invalid_review"


async def run(approval: str) -> None:
    if approval != DIGEST:
        raise ValueError("Explicit campaign approval digest required")
    campaign = load_campaign()
    key = os.environ.get("OPENROUTER_API_KEY") or dotenv_values(ROOT / ".env").get(
        "OPENROUTER_API_KEY"
    )
    if not key:
        raise ValueError("Configure key locally")
    journal = Journal(JOURNAL, campaign)
    try:
        async with httpx.AsyncClient(
            headers={"Authorization": "Bearer " + key},
            timeout=30,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            catalog = await client.get(API + "/models/" + MODEL + "/endpoints")
            catalog.raise_for_status()
            data = catalog.json()
            validate_catalog(data)
            endpoint = next(
                e for e in data["data"]["endpoints"] if e["tag"] == "deepinfra/bf16"
            )
            if "response_format" not in endpoint["supported_parameters"]:
                raise ValueError("Structured response support unavailable")
            for case in campaign["cases"]:
                if not journal.reserve(case["id"]):
                    continue
                try:
                    result = await asyncio.wait_for(
                        stream_reply(client, case["request_body"], output_limit=2048),
                        timeout=90,
                    )
                    check_review(case, result)
                except Exception as error:  # noqa: BLE001 — redact provider errors; halt without retry
                    result = {
                        "status": "failed",
                        "error_type": type(error).__name__,
                        "accounting_valid": False,
                        "cost_usd": None,
                    }
                result["request_sha256"] = case["request_sha256"]
                journal.settle(case["id"], result)
                if (
                    not result.get("accounting_valid")
                    or journal.report()["results"][-1]["state"] != "settled"
                ):
                    break
    finally:
        print(json.dumps(journal.report(), indent=2))
        journal.db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-campaign-sha256")
    args = parser.parse_args()
    try:
        if args.approved_campaign_sha256:
            asyncio.run(run(args.approved_campaign_sha256))
        else:
            campaign = load_campaign()
            print(
                json.dumps(
                    {
                        "status": "offline_preflight",
                        "paid_calls": 0,
                        "cases": len(campaign["cases"]),
                        "ceiling_usd": str(CEILING),
                        "campaign_sha256": DIGEST,
                    }
                )
            )
    except Exception as error:  # noqa: BLE001 — redact provider errors; halt without retry
        print("Stopped: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1) from None
