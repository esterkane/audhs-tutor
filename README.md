# AuDHS-Tutor
Personal, local-first, AuDHD-centred **learning operating system with AI capabilities** — AI/ML/programming plus language, guitar and movement blocks; text now, voice in Stage 5. Built with Claude Code.

Principle: *the LLM explains and reasons; the Learning Kernel remembers and decides.*

Start here: `docs/ARCHITECTURE.md` → `docs/ROADMAP.md` → `docs/adr/` → `docs/research/architecture-review-response.md`.
Setup (macOS, no Docker): `./scripts/bootstrap.sh`, fill `.env`, `make dev`, then in Claude Code: `/build-stage 0`.

Claude Code layout: `CLAUDE.md` (memory) · `.claude/rules/` (path-scoped rules) · `.claude/skills/` (procedures: build-stage, feature-slice, pedagogy-guardrails, audhd-ux, learning-events, llm-routing, db-migration, rag-ingest, tutor-eval, adr, handoff, commit) · `.claude/agents/` (code-reviewer, pedagogy-reviewer, tutor-evaluator, repo-researcher) · `.claude/hooks/` (session context, file protection, post-edit lint, stop check) · `.claude/settings.json` (permissions).
