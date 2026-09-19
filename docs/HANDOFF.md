# Handoff — 2026-09-19
Starter kit generated and reconciled with the Architecture Review Brief (see docs/research/architecture-review-response.md).
Stage 0 not started. Binding decisions: CLAUDE.md + ADR-0001…0010.
Next step: `./scripts/bootstrap.sh` → `make dev` → `claude` → `/build-stage 0`, then `/build-stage 1` (attention-mechanisms vertical slice).
Do not: reintroduce a LiteLLM proxy, LangGraph or multi-agent tutoring in Phase 1. Qdrant is the retrieval store from day one (ADR-0002); models are managed through the registry (ADR-0010), never hardcoded.
