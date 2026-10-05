# Shared agent instructions

Read `CLAUDE.md` for the shared architecture and working conventions, `docs/ARCHITECTURE.md` before structural work, and the applicable `.claude/rules/` files. Keep Claude Code skills and project memory intact.

Owner policy (2026-09-24): use local execution whenever accurate and capable. OpenAI is optional for demonstrated local gaps, with task-specific evaluation; configuring a key never authorizes a blanket routing switch. See `docs/CLAUDE-CONFIG-AUDIT.md`.

Before continuing, read the current checklist in `docs/CURRENT-WORK.md`, relevant sections of `docs/HANDOFF.md`, recent `docs/CODEX-CONTINUATION.md` entries, and the applicable stage in `docs/IMPROVEMENT-PLAN.md`. Preserve all inherited uncommitted work. Do not assume untracked files are disposable. Avoid concurrent edits by different coding agents.

For each bounded implementation slice, test it, record exact verification and outstanding work in the shared handoff/slice docs, and distinguish the new delta from inherited changes. Follow existing manual-only commit/ADR conventions. Do not mark a whole stage complete from a partial review.

## Owner visibility policy — 2026-10-01
Owner update 2026-10-05: this sanitized repository is PUBLIC again. The separate original archive must remain PRIVATE. This supersedes earlier both-private instructions: preserve all publication guards and exclusions for databases, acquired materials, acquisition scripts, private configuration and credentials. Keep the separate private archive and its history distinct.


## Efficient execution — owner request 2026-10-05
- Start with the current checklist and relevant slice records; read matching handoff sections and recent continuation entries, not the full accumulated history each turn. Preserve all applicable architecture, safety and learning invariants.
- Batch related changes into one coherent, reviewable slice and one final validation/publication cycle. Do not create separate cycles for every small copy/layout adjustment.
- Keep full command logs locally; return concise outcomes and relevant failure excerpts. Batch independent reads and avoid repeating unchanged file dumps.
- Reuse passing checks for unchanged code. Repeat or broaden checks when a change, failure or risk justifies it; retain relevant unit, browser, keyboard, visual and publication gates.
- Give reviewers bounded diffs, file paths, invariants and test evidence instead of full conversation history. Use agents only for concrete independent work where review or parallelism adds value.
- Keep progress updates brief and meaningful. Record evidence once in the slice document and link it from handoffs. Do not lower model quality, weaken tests or drop requirements to save tokens.


## Lower-credit execution — owner request 2026-10-05
- Finish one bounded task with one validation/publication cycle. Do not launch open-ended investigation loops; state the hypothesis and stopping criterion before a model experiment.
- Reuse verified results for unchanged code. Do not rerun whole suites for documentation-only changes, or publish separate documentation commits solely to report routine CI status; batch that evidence into the next relevant handoff.
- Use compact targeted file reads and concise logs. Keep progress updates minimal. Delegate only a concrete required review or independently useful task, with a bounded diff instead of conversation history.
- Preserve required correctness, security, learning, browser and accessibility checks. Saving credits never justifies weaker teaching models, dropping context or skipping a necessary gate.
