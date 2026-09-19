---
name: feature-slice
description: Implement one vertical feature slice the project way — schema, service, API route, UI, tests, learning-event logging, docs. Use for any new feature or endpoint; also auto-applies when Claude starts implementing a feature.
argument-hint: "[slice-name] [optional one-line spec]"
---
# Feature slice: $ARGUMENTS

Definition of done (all mandatory, in this order):
1. **Spec** — 3–6 lines in `docs/slices/<slice-name>.md`: user story, inputs/outputs, events emitted, mode/energy behaviour, accessibility note. If the spec touches pedagogy, run the checklist in `/pedagogy-guardrails`; if it touches a screen, run `/audhd-ux`.
2. **Schema** — Pydantic schemas in `backend/app/schemas/`; ORM changes via `/db-migration`.
3. **Kernel / orchestrator** — deterministic state logic in `backend/app/kernel/`; LLM-facing logic only in `backend/app/orchestrator/` via `ModelProvider` with an explicit `TaskClass` (`/llm-routing`). Emit events (`/learning-events`) and write `tutor_trace`/`model_call` rows. Retrieved text only via `context.data_block()`.
4. **API** — router in `backend/app/api/<name>.py`, registered in `api/__init__.py`. OpenAPI summary + response model on every route.
5. **Tests** — `backend/tests/test_<name>.py` (kernel + route; `FakeProvider` fixture; poisoned-chunk fixture if retrieval is involved). Run `make test-backend`.
6. **UI** — `frontend/src/features/<name>/` (api.ts hooks, components). Regenerate API types (`pnpm gen:api`). Component test in vitest. Run `make test-frontend`.
7. **Lint** — `make lint` green.
8. **Docs** — update `docs/ARCHITECTURE.md` only if a boundary changed; otherwise the slice doc is enough. Tick the slice in ROADMAP.

Keep the slice small enough to finish in one session. If it grows, split and note the remainder in HANDOFF.
