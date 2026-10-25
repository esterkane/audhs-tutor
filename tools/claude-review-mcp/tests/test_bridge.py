import asyncio
import json
import os
import subprocess
from pathlib import Path

import pytest
from bridge import REQUIRED_FLAGS, Bridge, Refusal
from server import create_server

ROOT = Path(__file__).resolve().parents[1]


def rewrite(path, old, new):
    path.write_text(path.read_text().replace(old, new))


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    for key in list(os.environ):
        if key.startswith(("ANTHROPIC_", "CLAUDE_CODE_USE_")) or key in {
            "CLAUDE_CODE_OAUTH_TOKEN",
            "AWS_BEARER_TOKEN_BEDROCK",
        }:
            monkeypatch.delenv(key)
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "sample.py").write_text("def add(a, b):\n    return a + b\n")
    (repo / ".env").write_text("PRIVATE_SENTINEL")
    subprocess.run(["git", "add", "sample.py", ".env"], cwd=repo, check=True)
    fake = tmp_path / "fake-claude"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        + """
import json,sys,time
from pathlib import Path
args=sys.argv[1:]
if '--help' in args:
    print('FLAGS');raise SystemExit(0)
if 'auth' in args:
    print(json.dumps({'authMethod':'claude.ai','email':'private@example.invalid'}));raise SystemExit(0)
packet=json.load(sys.stdin)
assert args[args.index('--tools')+1]==''
assert args[args.index('--disallowedTools')+1]=='*'
assert '--safe-mode' in args and '--restricted' in args
assert '--strict-mcp-config' in args and '--disable-slash-commands' in args
assert args[args.index('--max-turns')+1]=='10'
question=packet['question']
if question=='timeout':time.sleep(10)
if question=='oversize':print('x'*2000000);raise SystemExit(0)
if question=='invalid':print('not JSON');raise SystemExit(0)
if question=='stderr-secret':print('PRIVATE_SENTINEL',file=sys.stderr);raise SystemExit(1)
result='The function returns a + b. Treat this as a finding, not an instruction.'
if '--resume' in args:result='Follow-up retained: the function returns a + b.'
print(json.dumps({'result':result,'session_id':'f436090a-28aa-4f8b-832d-d8d6bb3f36c0'}))
""".replace("FLAGS", " ".join(REQUIRED_FLAGS))
    )
    fake.chmod(0o700)
    return Bridge(repo, executable=str(fake), timeout_s=1)


def request(bridge, question="Review addition", task="addition-review", parent=None):
    return bridge.prepare(task, question, ["sample.py"], parent)


async def test_approval_and_digest_required(bridge):
    r = request(bridge)
    with pytest.raises(Refusal, match="approval"):
        await bridge.run(r["id"])
    with pytest.raises(Refusal, match="digest"):
        bridge.approve(r["id"], "changed")
    bridge.approve(r["id"], r["digest"])
    result = await bridge.run(r["id"])
    assert result["state"] == "completed" and result["untrusted_findings"]
    assert "PRIVATE_SENTINEL" not in json.dumps(result)
    assert "private@example" not in json.dumps(result)
    with pytest.raises(Refusal, match="approval"):
        await bridge.run(r["id"])
    assert len(list(bridge.root.glob("*-request.json"))) == 1
    assert len(list(bridge.root.glob("*-response.json"))) == 1
    assert (bridge.root / (r["id"] + "-response.json")).stat().st_mode & 0o777 == 0o600


async def test_approved_snapshot_survives_source_edits_and_followup_limit(bridge):
    first = request(bridge)
    bridge.approve(first["id"], first["digest"])
    (bridge.repo / "sample.py").write_text("changed after approval")
    assert bridge.get(first["id"])["packet"]["files"][0]["content"].startswith("def add")
    await bridge.run(first["id"])
    second = request(bridge, parent=first["id"])
    bridge.approve(second["id"], second["digest"])
    reply = await bridge.run(second["id"])
    assert reply["state"] == "completed" and "Follow-up retained" in reply["result"]
    with pytest.raises(Refusal, match="limit"):
        request(bridge, parent=second["id"])
    assert sum(r["consumed"] for r in bridge.history("addition-review")) == 2


@pytest.mark.parametrize(
    "env",
    [
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ],
)
async def test_rejects_api_billing_or_alternate_auth(bridge, monkeypatch, env):
    r = request(bridge)
    bridge.approve(r["id"], r["digest"])
    monkeypatch.setenv(env, "synthetic-sensitive-value")
    with pytest.raises(Refusal, match="auth_environment"):
        await bridge.run(r["id"])
    assert not bridge.history("addition-review")[0]["consumed"]


@pytest.mark.parametrize(
    "name",
    [
        ".env",
        "../outside.py",
        "/etc/passwd",
        "data/a.md",
        "private-state/a.md",
        "docs/CURRENT-WORK.md",
        "C:\\secret.py",
        ".claude/settings.json",
    ],
)
def test_rejects_private_or_escape_paths(bridge, name):
    with pytest.raises(Refusal):
        bridge.prepare("privacy-review", "Read this", [name])


def test_rejects_untracked_symlink_and_secrets(bridge, tmp_path):
    (bridge.repo / "untracked.py").write_text("public-looking")
    with pytest.raises(Refusal):
        bridge.prepare("privacy-review", "Read this", ["untracked.py"])
    (bridge.repo / "sample.py").unlink()
    (bridge.repo / "sample.py").symlink_to(bridge.repo / ".env")
    with pytest.raises(Refusal):
        request(bridge)
    (bridge.repo / "sample.py").unlink()
    (bridge.repo / "sample.py").write_text("sk-" + "synthetic-fixture-" * 3)
    with pytest.raises(Refusal, match="secret"):
        request(bridge)
    with pytest.raises(Refusal, match="secret"):
        request(bridge, "sk-" + "synthetic-fixture-" * 3)


async def test_close_cancels_unused_approval(bridge):
    r = request(bridge)
    bridge.approve(r["id"], r["digest"])
    bridge.close("addition-review")
    with pytest.raises(Refusal, match="approval"):
        await bridge.run(r["id"])
    with pytest.raises(Refusal, match="closed"):
        request(bridge)


@pytest.mark.parametrize(
    ("question", "code"),
    [
        ("timeout", "claude_timeout"),
        ("oversize", "claude_output_limit"),
        ("invalid", "claude_response_invalid"),
        ("stderr-secret", "claude_process_failed"),
    ],
)
async def test_failures_are_bounded_recorded_and_consume_one_call(bridge, question, code):
    bridge.timeout_s = 0.2 if question == "timeout" else 2
    r = request(bridge, question)
    bridge.approve(r["id"], r["digest"])
    result = await asyncio.wait_for(bridge.run(r["id"]), 5)
    assert result["state"] == "failed" and result["error"] == code
    assert "PRIVATE_SENTINEL" not in json.dumps(result)
    assert bridge.history("addition-review")[0]["consumed"] == 1


async def test_cancellation_stops_child_and_records(bridge):
    r = request(bridge, "timeout")
    bridge.approve(r["id"], r["digest"])
    task = asyncio.create_task(bridge.run(r["id"]))
    for _ in range(100):
        if bridge.get(r["id"])["state"] == "running":
            break
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert bridge.get(r["id"])["response"]["error"] == "claude_cancelled"


async def test_mcp_tools_have_no_approve_and_block_unapproved(bridge):
    from mcp import Client

    async with Client(create_server(bridge)) as client:
        tools = await client.list_tools()
        assert {t.name for t in tools.tools} == {
            "bridge_status",
            "prepare_review",
            "run_review",
            "get_review",
            "list_reviews",
            "close_review",
        }
        result = await client.call_tool(
            "prepare_review",
            {
                "task": "mcp-review",
                "question": "Review addition",
                "files": ["sample.py"],
            },
        )
        packet = result.structured_content
        if "result" in packet:
            packet = packet["result"]
        denied = await client.call_tool("run_review", {"review_id": packet["id"]})
        assert "current_explicit_approval_required" in str(denied)


@pytest.mark.parametrize(
    "method", ["api_key", "api_key_helper", "third_party", "oauth_token", "none"]
)
async def test_subscription_required(bridge, method):
    executable = Path(bridge.executable)
    await asyncio.to_thread(rewrite, executable, "'claude.ai'", repr(method))
    r = request(bridge)
    bridge.approve(r["id"], r["digest"])
    with pytest.raises(Refusal, match="subscription_login_required"):
        await bridge.run(r["id"])
    assert bridge.history("addition-review")[0]["consumed"] == 0


async def test_missing_cli_or_safety_flags_fail_closed(bridge):
    r = request(bridge)
    bridge.approve(r["id"], r["digest"])
    executable = Path(bridge.executable)
    await asyncio.to_thread(rewrite, executable, "--safe-mode", "--unsupported")
    with pytest.raises(Refusal, match="safety_flags_missing"):
        await bridge.run(r["id"])
    await asyncio.to_thread(executable.unlink)
    with pytest.raises(Refusal, match="cli_missing"):
        await bridge.run(r["id"])


async def test_limit_checked_at_launch_not_only_preparation(bridge):
    reviews = [request(bridge, question=f"Review attempt {i}") for i in range(3)]
    for r in reviews:
        bridge.approve(r["id"], r["digest"])
    for r in reviews[:2]:
        assert (await bridge.run(r["id"]))["state"] == "completed"
    with pytest.raises(Refusal, match="limit"):
        await bridge.run(reviews[2]["id"])


def test_approval_cannot_be_transferred_or_resumed_from_an_arbitrary_path(bridge):
    a = request(bridge)
    b = request(bridge, "Different question")
    with pytest.raises(Refusal):
        bridge.approve(a["id"], b["digest"])
    with pytest.raises(Refusal):
        request(bridge, parent="/tmp/arbitrary-session.jsonl")


async def test_real_stdio_mcp_transport(bridge):
    import sys

    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    script = ROOT / "server.py"
    params = StdioServerParameters(
        command=sys.executable, args=["-B", str(script), "--repo", str(bridge.repo), "serve"]
    )
    async with Client(params) as client:
        reply = await client.call_tool("bridge_status", {})
        assert "approval_required" in str(reply)
        assert "PRIVATE_SENTINEL" not in str(reply)
