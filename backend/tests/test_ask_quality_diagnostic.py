"""Offline diagnostic contracts, not model-quality assertions."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models_ai.provider import Message, ProviderResult


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
        return SimpleNamespace(
            result=ProviderResult(
                model="synthetic",
                provider="ollama",
                text="Original model output",
                parsed={"claims": []},
                raw={"transport": "excluded"},
            )
        )

    underlying = SimpleNamespace(router=object(), complete=complete)
    gateway = module.CandidateGateway(underlying, "Candidate rule")
    packet = [Message(role="system", content="Original"), Message(role="user", content="Question")]
    result = await gateway.complete("chat", packet)
    assert result.result.text == "Original model output"
    assert gateway.responses[0]["parsed"] == {"claims": []}
    assert "raw" not in gateway.responses[0]
    assert packet[0].content == "Original"
    assert seen[0][0].content == "Original\nCandidate rule"
    assert seen[0][1] == packet[1]
    assert gateway.router is underlying.router
    assert gateway.packets[0][0]["content"] == seen[0][0].content


@pytest.mark.parametrize("fail_before_inference", [False, True])
async def test_run_persists_rejected_output_and_stops_without_retry(
    monkeypatch, tmp_path, fail_before_inference
):
    from contextlib import asynccontextmanager

    module = load(monkeypatch)
    cases = [
        {"id": "completed", "criteria": [], "history": [], "question": "First"},
        {
            "id": "failed",
            "criteria": ["Reject invented evidence"],
            "history": [],
            "question": "Explain",
        },
        {"id": "must-not-run", "criteria": [], "history": [], "question": "Later"},
    ]
    monkeypatch.setattr(
        module, "load_inputs", lambda _: (json.dumps({"cases": cases}).encode(), "")
    )
    monkeypatch.setattr(module, "model_manifest", lambda: {"name": "offline-fixture"})
    monkeypatch.setattr(module, "local_settings", lambda value: value)
    closed = []

    @asynccontextmanager
    async def session_factory():
        yield None

    async def close():
        closed.append(True)

    async def open_world(*args, **kwargs):
        return SimpleNamespace(session_factory=session_factory, learner_id="synthetic", close=close)

    async def complete(*args, **kwargs):
        return SimpleNamespace(
            result=ProviderResult(
                model="synthetic",
                provider="ollama",
                text="Rejected output",
                parsed={"invalid": True},
            )
        )

    async def pinned_gateway(*args):
        return SimpleNamespace(router=object(), complete=complete)

    calls = []

    async def respond(db, gateway, *args):
        calls.append(True)
        if len(calls) == 1 or not fail_before_inference:
            await gateway.complete("chat", [Message(role="user", content="Synthetic question")])
        if len(calls) == 1:
            return SimpleNamespace(model_dump=lambda **kwargs: {"text": "Saved first reply"})
        raise ValueError("Exact binding rejected")

    monkeypatch.setattr(module, "open_world", open_world)
    monkeypatch.setattr(module, "pinned_gateway", pinned_gateway)
    monkeypatch.setattr(module, "respond", respond)
    path = tmp_path / "report.json"
    with pytest.raises(ValueError, match="Exact binding"):
        await module.run(path, None)
    report = json.loads(path.read_text())
    assert len(report["results"]) == len(calls) == 2
    assert report["results"][0]["outcome"] == "completed"
    result = report["results"][1]
    assert result["outcome"] == "failed"
    assert "reply" not in result
    if fail_before_inference:
        assert result["provider_response"] is None
        assert result["packet"] is None
        assert result["generation_settings"] is None
    else:
        assert result["provider_response"]["parsed"] == {"invalid": True}
        assert result["packet"][0]["content"] == "Synthetic question"
    assert closed == [True]
