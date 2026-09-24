# Claude Code continuity audit — 2026-09-24

Reviewed all project instructions and tooling before continuation:

- `CLAUDE.md`, `AGENTS.md`, architecture, improvement plan, handoff and continuation notes.
- 12 skills: adr, audhd-ux, build-stage, commit, db-migration, feature-slice, handoff,
  learning-events, llm-routing, pedagogy-guardrails, rag-ingest, tutor-eval.
- Four path rules: backend, frontend, data-and-events, prompts-and-pedagogy.
- Four agent definitions: code-reviewer, pedagogy-reviewer, repo-researcher, tutor-evaluator.
- Four hooks: session-start, protected-file guard, post-edit checks, stop reminder.
- Project settings, local settings (structure only; no secret values), local-settings example,
  launch configurations and `.mcp.json`. No additional global skill/command files or global/project
  MCP entries were found in the inspected user-level Claude configuration.

## Binding continuation policy

The owner explicitly requires local execution whenever it is accurate and capable. Local Python,
validation, learner-state logic, retrieval, embeddings, speech and suitable LLM tasks remain local.
OpenAI is the cheaper optional hosted provider for demonstrated gaps, not the new default for all
learning. A key's presence and a transport benchmark are not evidence of tutoring/grading quality.
Keep evidence per task and record model/route/cost. Do not enable Claude spend merely because an
Anthropic key exists. Existing specialist hosted roles still need separate quality/route review;
this provider slice does not certify every inherited route as the optimal local/hosted choice.

Tests/benchmarks use disposable databases. Never test on the learner DB. Keep API keys private,
accepted ADRs immutable, prompts versioned, skill instructions available to Claude, and actual
review/test/eval outcomes in the handoff. Owner already authorized implementation, commits and push;
do not re-request those merely because manual-only skill defaults say to offer them.

## MCP and hooks

`qdrant-docs` is an optional generic fetch server, not Qdrant database access. `sqlite-learner`
points to `data/dev.db`; its former comment called this read-only without an enforced restriction.
Automatic enabling is now disabled. Prefer explicit SQLite `mode=ro` connections or disposable
copies for inspection; only re-enable a database connector after verifying its actual tool scope.
Neither configured MCP server was launched during this audit; configuration presence is not a
connectivity or read-only guarantee. Codex uses available tools and equivalent local checks;
Claude-specific hooks do not automatically run in Codex.

The protected-file hook intentionally blocks `.env*` (including `.env.example`), runtime data and
accepted ADR edits. Leave secrets to local manual configuration; do not weaken those protections.
Post-edit formatting, lint, test marker and independent review must still be performed explicitly
when working outside Claude's hooks. Local Claude model selection is personal tooling configuration,
not the application's provider routing. It was preserved.

## Stale guidance reconciled

The routing skill previously described future MLX TTS and pre-reservation budget behavior, despite
Kokoro and reservation accounting already existing. Updated its operational rules for OpenAI,
current TTS and paid benchmarks. Historical handoff entries remain history; read the newest section
first. The latest continuation pointer links the active handoff so Claude resumes current work.
