"""Offline manifest integrity, not a semantic scorer or database/model evaluation."""

import ast
import copy
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "evals/cases/project-postgres-causal.json"


def manifest():
    return json.loads(MANIFEST.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(data):
    require(data["schema_version"] == 1, "manifest version")
    require(data["qualification_status"] == "not_run", "fixture is not a run result")
    contract = data["review_contract"]
    require(contract["semantic_verdict"] == "manual_evidence_review", "manual review required")
    require(contract["allowed_verdicts"] == ["pass", "fail", "unresolved"], "tri-state review")
    require(contract["missing_review_verdict"] == "unresolved", "missing review cannot pass")
    require(
        {"manifest_sha256", "transcript_sha256", "oracle_report_sha256_or_unavailable", "criteria"}
        <= set(contract["receipt_required_fields"]),
        "review provenance",
    )
    require(
        {
            "criterion_id",
            "verdict",
            "answer_excerpt",
            "source_passage_or_oracle_observation",
            "reason",
        }
        <= set(contract["criterion_required_fields"]),
        "claim-level evidence",
    )
    sources = data["sources"]
    for url in sources.values():
        parsed = urlparse(url)
        require(
            parsed.scheme == "https"
            and parsed.netloc == "www.postgresql.org"
            and parsed.path.startswith("/docs/17/"),
            "versioned official source",
        )
    bindings = data["oracle_bindings"]
    for item in bindings.values():
        require(item["script"] == "scripts/postgres_accuracy.py", "known oracle")
        require("expected" in item, "explicit expected value including null")
        if item["availability"] == "implemented":
            require(
                bool(item["report_path"]) and item["proposed_report_path"] is None,
                "implemented oracle path",
            )
        else:
            require(item["availability"] == "planned", "oracle availability")
            require(
                item["report_path"] is None and bool(item["proposed_report_path"]),
                "planned oracle must not claim executable evidence",
            )
    cases = data["cases"]
    require(len(cases) == 8, "eight bilingual cases")
    require(len({case["id"] for case in cases}) == len(cases), "unique case identity")
    groups = defaultdict(list)
    used_bindings = set()
    for case in cases:
        require(case["postgres_major"] == 17, "matching database version")
        require(case["language"] in {"en", "de"}, "supported language")
        require(case["id"] == case["family"] + "-" + case["language"], "stable case identity")
        require(isinstance(case["prompt"], str) and len(case["prompt"]) > 80, "complete scenario")
        required, forbidden = case["required_claims"], case["forbidden_claims"]
        require(required and forbidden, "both positive and negative criteria")
        ids = [claim["id"] for claim in required + forbidden]
        require(len(set(ids)) == len(ids), "unique criterion identity")
        for claim in required + forbidden:
            require(
                isinstance(claim["claim"], str) and len(claim["claim"]) > 20,
                "substantive criterion",
            )
        for claim in required:
            require(
                claim["source_ids"] and set(claim["source_ids"]) <= sources.keys(),
                "known factual sources",
            )
            require(set(claim["oracle_binding_ids"]) <= bindings.keys(), "known oracle binding")
            used_bindings.update(claim["oracle_binding_ids"])
        groups[case["family"]].append(case)
    require(len(groups) == 4, "four factual families")
    for pair in groups.values():
        require(
            len(pair) == 2 and {case["language"] for case in pair} == {"en", "de"},
            "one English and one German case",
        )
        require(
            pair[0]["required_claims"] == pair[1]["required_claims"]
            and pair[0]["forbidden_claims"] == pair[1]["forbidden_claims"],
            "language-independent factual criteria",
        )
        require(pair[0]["prompt"] != pair[1]["prompt"], "translated prompt")
    require(used_bindings == bindings.keys(), "no disconnected oracle claims")


def test_manifest_is_a_bilingual_review_contract_not_a_score():
    validate(manifest())


def test_implemented_bindings_exist_in_current_oracle_report_shape():
    # Read source AST only: do not start Docker or connect to any database.
    module = ast.parse((ROOT / "scripts/postgres_accuracy.py").read_text())
    functions = {
        node.name: node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def returned_dict(name):
        values = [
            node.value
            for node in ast.walk(functions[name])
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
        ]
        assert len(values) == 1
        return {
            ast.literal_eval(key): value
            for key, value in zip(values[0].keys, values[0].values, strict=True)
        }

    report = returned_dict("run")
    rls = report["rls"]
    assert isinstance(rls, ast.Dict)
    paths = {"rls." + ast.literal_eval(key) for key in rls.keys}
    concurrency = report["concurrency"]
    assert isinstance(concurrency, ast.ListComp)
    assert ast.literal_eval(concurrency.generators[0].iter) == ("REPEATABLE READ", "SERIALIZABLE")
    paths.update(f"concurrency.{index}.{key}" for index in (0, 1) for key in returned_dict("skew"))
    for family in ("null_comparisons", "read_committed"):
        paths.update(f"{family}.{key}" for key in returned_dict(family))
    for binding in manifest()["oracle_bindings"].values():
        if binding["availability"] == "implemented":
            assert binding["report_path"] in paths
        else:
            assert binding["report_path"] is None


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_case",
        "unknown_source",
        "unknown_oracle",
        "planned_as_implemented",
        "missing_review_pass",
        "language_drift",
        "duplicate_criterion",
        "mutable_documentation",
    ],
)
def test_corrupted_or_overclaimed_manifest_is_rejected(change):
    data = copy.deepcopy(manifest())
    if change == "duplicate_case":
        data["cases"][1]["id"] = data["cases"][0]["id"]
    elif change == "unknown_source":
        data["cases"][0]["required_claims"][0]["source_ids"] = ["invented"]
    elif change == "unknown_oracle":
        data["cases"][0]["required_claims"][0]["oracle_binding_ids"] = ["invented"]
    elif change == "planned_as_implemented":
        binding = data["oracle_bindings"]["null-not-in"]
        binding["proposed_report_path"] = binding["report_path"]
        binding["report_path"] = None
        binding["availability"] = "implemented"
    elif change == "missing_review_pass":
        data["review_contract"]["missing_review_verdict"] = "pass"
    elif change == "language_drift":
        data["cases"][1]["required_claims"][0]["claim"] += " Changed conclusion."
    elif change == "duplicate_criterion":
        case = data["cases"][0]
        case["forbidden_claims"][0]["id"] = case["required_claims"][0]["id"]
    else:
        data["sources"]["policy"] = "https://www.postgresql.org/docs/current/sql-createpolicy.html"
    with pytest.raises(ValueError):
        validate(data)
