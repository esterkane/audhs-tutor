# OpenAI hosted provider

Learners can configure an OpenAI key and evaluate the cheaper hosted candidate without changing existing task routes.
Inputs: server-side OPENAI_API_KEY, registry model/prices, existing messages and typed schemas. Outputs: completions/streams and provider-specific readiness.
All hosted calls, including benchmarks, reserve the shared daily budget and write model_call usage; no learning-state changes.
Mode/energy and teaching policy remain unchanged; activation follows a real tutoring evaluation, not a successful connection alone.
Models controls distinguish key setup from downloading and explain paid benchmarks; keyboard-accessible native controls.

## Implemented

- Separate OpenAI adapter (LiteLLM + Instructor), key, source/runtime and registry candidate;
  Anthropic/local choices and all existing task assignments preserved.
- Plain/typed/streamed responses; reasoning disabled for verified Chat Completions tool support,
  one transport attempt, sanitized errors, prompt-size bound, unknown models rejected.
- Conservative input estimate uses $0.125/M cache-write ceiling; output $0.50/M. No SDK cost
  estimate is mislabelled as an invoice. See `docs/PROVIDER-COST-COMPARISON.md`.
- Shared cap includes OpenAI; paid benchmarks use a pinned gateway without fallback and the API's
  shared reservation lock. Schemas/wrapper allowance are reserved; interrupted streams lacking
  final usage retain unknown/reserved cost and promptly close their transport.
- Models UI explains configured vs verified, key setup vs download, and paid benchmarks. Custom
  entries require positive prices and a verified API model; they do not silently become free.
- Both hosted keys disabled in sandbox; key excluded from backup settings. No new dependency,
  migration, learning event type or prompt changes. No live learner-state writes.

## Acceptance and evidence

- [x] Adapter contract/key separation/registry validation: `test_openai_provider.py`.
- [x] Cap blocks requests before provider invocation, includes schemas, records paid benchmarks
  and retains stopped-stream billing: provider and usage-accounting regression suites.
- [x] Full frontend tests (57); generated API contract unchanged; eight isolated browser journeys.
- [x] Real synthetic API compatibility: completion, typed output and streaming; six requests,
  $0.000725 conservative estimate. `evals/results/report-2026-09-24-openai.md`.
- [ ] General tutoring/grading quality acceptance and task-specific live assignment: not claimed.
  Luna corrected the whitespace explanation but hints still gave several algorithm steps.
- Backend final suite/lint result recorded in the latest handoff after final verification.

## Review fixes

Read-only code review identified schema reservation and partial-stream accounting gaps; fixed with
regressions. Re-review found no remaining blocker/major. Restricted OpenAI to verified registry
models rather than claiming arbitrary model parameter compatibility. The stronger reservation
changed the concurrency test's expected admission count from two calls to one at its fixed cap;
the same overspend-prevention behavior remains verified.

## Local-first and continuation

The owner clarified: perform work locally wherever accurate/capable, and use OpenAI only when
needed. Key setup is not routing activation. Existing local correctness shortcomings are recorded;
model self-confidence is not an accuracy gate. Evaluate capability-specific fallbacks before
changing assignments. No automatic content-correctness escalation is implemented in this slice.
See `docs/CLAUDE-CONFIG-AUDIT.md` for the complete shared tooling review.

Known limit: independent CLI/backend processes use separate budget locks; do not run paid CLI
benchmarks concurrently with paid app requests. Registry pricing remains configurable and must
match provider rates; this is local spend estimation, not provider-side billing enforcement.

