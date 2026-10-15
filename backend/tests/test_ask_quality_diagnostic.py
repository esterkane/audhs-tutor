"""Offline diagnostic contracts, not model-quality assertions."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from app.models_ai.provider import Message


def load(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "ask_quality_diagnostic", scripts / "eval_ask_quality.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_cases_are_distinct_and_bounded(monkeypatch):
    module = load(monkeypatch)
    raw, candidate = module.load_inputs(None)
    cases = json.loads(raw)["cases"]
    assert candidate == ""
    assert {case["id"] for case in cases} == {
        "statistic-versus-weight",
        "units-transfer",
        "pressure-without-evidence",
    }
    assert all(case["criteria"] and len(case["question"]) <= 2000 for case in cases)
    assert all(len(case["history"]) <= 3 for case in cases)


async def test_candidate_changes_only_copied_system_message(monkeypatch):
    module = load(monkeypatch)
    seen = []

    async def complete(task, packet, **kwargs):
        seen.append(packet)
        return "result"

    underlying = SimpleNamespace(router=object(), complete=complete)
    gateway = module.CandidateGateway(underlying, "Candidate rule")
    packet = [Message(role="system", content="Original"), Message(role="user", content="Question")]
    assert await gateway.complete("chat", packet) == "result"
    assert packet[0].content == "Original"
    assert seen[0][0].content == "Original\nCandidate rule"
    assert seen[0][1] == packet[1]
    assert gateway.router is underlying.router
    assert gateway.packets[0][0]["content"] == seen[0][0].content
