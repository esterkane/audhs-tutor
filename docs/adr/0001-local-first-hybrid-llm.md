# 0001 — Local-first app; ModelProvider interface with inspectable routing (no proxy in Phase 1)
Date: 2026-09-19
Status: Accepted
## Context
Single learner, M4 Pro 48 GB, low cost and privacy matter. Frontier quality is needed only for rubric grading, deep explanation, code review and conflicting-evidence resolution. A separate LiteLLM proxy container adds ops for a solo developer without value in Phase 1; opaque routers must not choose models for reasons the app cannot inspect.
## Decision
Localhost web app (FastAPI + React/Vite). `ModelProvider` interface with `OllamaProvider` (general local inference) and `ClaudeProvider` (hosted), implemented over the LiteLLM Python SDK. A routing table `TaskClass → (provider, model, fallback)` lives in `models_ai/routing.py` and is logged on every `model_call`. Daily hosted budget enforced in-app by summing `model_call.cost`. Claude is available from Phase 1 but only for `grade_rubric`, `tutor_deep`, `code_review`, `conflict_resolution`. MLX is used only for STT/TTS.
## Consequences
+ Zero containers, inspectable routing, ~$8–25/month. − Budget/caching logic is ours to maintain; a proxy can be reintroduced later as a provider implementation if needed.
## Alternatives considered
LiteLLM proxy (deferred), all-hosted, all-local, Ollama+MLX dual general stack (rejected: two stacks without measured need).
## Evidence / sources
docs/research/phase1-architecture-v1.1.md §1–2; architecture review brief §14–15.
