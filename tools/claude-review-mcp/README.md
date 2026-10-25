# Approval-gated Claude review MCP

This local stdio MCP server lets Codex prepare a bounded code review, obtain explicit owner
approval, call Claude Code once, retain private history, and resume one approved follow-up.
It uses the official Python MCP SDK in a separate locked environment; no tutor dependency,
model route, database schema or hosted budget is changed. The doctor command is separate.

```sh
uv sync --frozen --project tools/claude-review-mcp
tools/claude-review-mcp/.venv/bin/python -B tools/claude-review-mcp/server.py --repo "$PWD" serve
```

Configure this as a local stdio MCP server in Codex. Use absolute paths and a 660-second tool
timeout (the review subprocess limit is600 seconds). On Windows, run it through the intended
WSL distribution and its normal user; native Windows process-group cancellation is not supported.
On macOS/Linux the same Python command works directly. Keep machine paths/config out of Git.
The server must not be exposed as a public HTTP endpoint. See official
[Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

Tools: `bridge_status`, `prepare_review`, `run_review`, `get_review`, `list_reviews`, `close_review`.
Approval is NOT a tool. After the owner approves the exact snapshot:

```sh
tools/claude-review-mcp/.venv/bin/python -B tools/claude-review-mcp/server.py \
  --repo "$PWD" approve REVIEW_UUID PACKET_SHA256
```

The operator must inspect the private request file before approval if needed. Follow
[`WORKFLOW.md`](../../docs/agent-handoffs/WORKFLOW.md). Approval is single-use/30 minutes; all
launched calls count toward the two-per-task limit. No reviewed commands are executed and
no second consultation is launched automatically. Missing/old Claude CLI, unsupported safety
flags or missing subscription login fail closed before inference. A failed review is retained
and consumes its launch allowance. Crashed `running` attempts stay consumed, never auto-retry.

Install Claude Code from its [official setup guide](https://code.claude.com/docs/en/setup),
then sign in yourself using `claude auth login`. The bridge requires authMethod `claude.ai`;
API-key/helper, third-party and token-environment authentication are rejected. Nonempty
ANTHROPIC_* and alternate-provider routing variables are rejected, never silently stripped.
This prevents accidental API-key routing; it is NOT a promise of free usage or a subscription
quota/extra-usage meter. Check your Claude account's allowance and extra-usage settings.
No account, login or provider settings are modified by the bridge itself.

Claude receives only the approved text snapshot, never the project directory as its working
directory. Built-in tools are disabled (`--tools ""`, `--disallowedTools "*"`), MCP configuration
is empty/strict, safe/restricted modes are required, customizations/slash commands are disabled
and hooks disabled via explicit settings. CLI flags are verified locally before each review.
The bridge deliberately does NOT allow Read/Grep/Glob: those would still allow broader file
access without a real sandbox. Current flags are documented in the official
[Claude CLI reference](https://code.claude.com/docs/en/cli-reference).

Only selected tracked UTF-8 code/documentation files are accepted, up to 8 files / 64 KB total.
Runtime/private directories, local handoffs, research notes, environment files, symlinks and
path escapes are rejected. Obvious credential patterns are refused in prompts/files/replies.
This scan is a heuristic, not proof that text contains no private data: the owner still reviews
the snapshot before approval. CLI installation and administrator-managed policy are trusted;
flags are defense in depth, not an OS sandbox. Private files/SQLite ledger are mode 600 in a
mode 700 folder. Stdout is MCP only; raw CLI stderr/auth output is never returned or saved.

Tests need no real Claude account and make no model calls:

```sh
uv run --frozen --project tools/claude-review-mcp pytest -q tools/claude-review-mcp/tests
```

The suite tests official-SDK in-memory and real stdio transport plus a deterministic fake CLI:
approval, no approval tool, API-auth refusal, resume, task limits at launch, secret/path rejection,
frozen snapshots, closed tasks, cancellation, malformed/oversized output and timeouts.
