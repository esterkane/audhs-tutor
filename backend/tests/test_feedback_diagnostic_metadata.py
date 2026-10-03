"""Diagnostic provenance must distinguish prompt reuse from runtime integration."""

import hashlib
import importlib.util
from pathlib import Path

from app.models_ai.provider import TaskClass
from app.orchestrator import playground, prompts


def diagnostic_module():
    path = Path(__file__).resolve().parents[2] / "scripts/eval_quoted_feedback.py"
    spec = importlib.util.spec_from_file_location("feedback_diagnostic", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reports_actual_builder_and_distinguishes_gateway_from_runtime():
    diagnostic = diagnostic_module()
    metadata = diagnostic.diagnostic_metadata("local-test")
    assert diagnostic.messages is playground.messages
    assert metadata["runtime_prompt_version"] == playground.VERSION
    assert metadata["runtime_request_intent"] == "check_answer"
    assert metadata["diagnostic_gateway_task"] == str(diagnostic.DIAGNOSTIC_TASK)
    assert diagnostic.DIAGNOSTIC_TASK == TaskClass.EXPLAIN_SIMPLE
    assert metadata["production_task"] == str(TaskClass.ANSWER_FEEDBACK)
    assert metadata["production_routing_exercised"] is False
    assert metadata["runtime_respond_exercised"] is False
    assert metadata["fallback_allowed"] is False
    assert "live_integration" not in metadata
    assert "task_prompt_sha256" not in metadata


def test_fragment_hash_follows_actual_runtime_loader(monkeypatch):
    diagnostic = diagnostic_module()
    monkeypatch.setattr(prompts, "answer_feedback_task", lambda: "changed runtime fragment")
    first = diagnostic.diagnostic_metadata("local-test")
    assert (
        first["feedback_task_fragment_sha256"]
        == hashlib.sha256(b"changed runtime fragment").hexdigest()
    )
    monkeypatch.setattr(prompts, "answer_feedback_task", lambda: "another runtime fragment")
    second = diagnostic.diagnostic_metadata("local-test")
    assert first["feedback_task_fragment_sha256"] != second["feedback_task_fragment_sha256"]
