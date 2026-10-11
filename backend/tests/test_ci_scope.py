"""CI reuse requires exact successful evidence; uncertainty runs all gates."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "ci_scope", Path(__file__).resolve().parents[2] / "scripts/ci_scope.py"
)
assert spec and spec.loader
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


@pytest.mark.parametrize(
    "paths,expected",
    [
        (["README.md", "docs/a.md"], True),
        ([], False),
        (["docs/a.json"], False),
        (["backend/app.py", "docs/moved.md"], False),
        ([".github/workflows/ci.yml"], False),
    ],
)
def test_paths(paths, expected):
    assert scope.markdown_only(paths) is expected


@pytest.mark.parametrize(
    "status,result,expected",
    [
        ("completed", "success", True),
        ("completed", "failure", False),
        ("in_progress", None, False),
        ("completed", "cancelled", False),
    ],
)
def test_evidence(status, result, expected):
    runs = [{"headSha": "a" * 40, "status": status, "conclusion": result}]
    assert scope.green_predecessor(runs, "a" * 40) is expected
    assert not scope.green_predecessor(runs, "b" * 40)
    assert not scope.green_predecessor([], "a" * 40)


@pytest.mark.parametrize(
    "error", [ValueError(), KeyError(), OSError(), subprocess.TimeoutExpired("gh", 45)]
)
def test_fail_closed(monkeypatch, capsys, error):
    def fail():
        raise error

    monkeypatch.setattr(scope, "needs_runtime", fail)
    scope.main()
    assert capsys.readouterr().out == "runtime=true\n"


def test_pr(monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setattr(scope, "command", lambda _: pytest.fail("PR attempted reuse"))
    assert scope.needs_runtime()


def test_push_checks_exact_base_and_latest_run(tmp_path, monkeypatch):
    import json

    before, head = "a" * 40, "b" * 40
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"before": before}))
    for key, value in {
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_EVENT_PATH": str(event),
        "GITHUB_SHA": head,
        "GITHUB_REPOSITORY": "example/repo",
    }.items():
        monkeypatch.setenv(key, value)
    calls = []

    def command(args):
        calls.append(args)
        if args[0] == "gh":
            return json.dumps([{"headSha": before, "status": "completed", "conclusion": "success"}])
        return "docs/a.md\0README.md\0" if "diff" in args else ""

    monkeypatch.setattr(scope, "command", command)
    assert not scope.needs_runtime()
    assert calls[1] == ["git", "diff", "--no-renames", "--name-only", "-z", before, head]
    assert "--status" not in calls[2]
    assert calls[2][calls[2].index("--limit") + 1] == "1"
