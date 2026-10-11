"""Diagnostic input failures must precede model or database access."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "workspace_case", ROOT / "scripts/eval_workspace_case.py"
)
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["same_path", "remote", "grading"])
async def test_rejects_before_world(tmp_path, monkeypatch, failure):
    case = json.loads((ROOT / "evals/workspace/retention-consistency.json").read_text())
    if failure == "grading":
        case["intent"] = "check_answer"
    source = tmp_path / "case.json"
    source.write_text(json.dumps(case))
    output = source if failure == "same_path" else tmp_path / "result.json"
    world = AsyncMock()
    monkeypatch.setattr(runner, "open_world", world)
    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: SimpleNamespace(
            ollama_host="https://example.com" if failure == "remote" else "http://127.0.0.1:11434"
        ),
    )
    with pytest.raises(ValueError):
        await runner.run(source, output)
    world.assert_not_awaited()
    assert json.loads(source.read_text()) == case
    if output != source:
        assert not output.exists()
