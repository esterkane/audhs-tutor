# Session latency observability — research reconciliation

2026-10-12. Next bounded latency slice after AU-EXPERIMENTS-01. The learner needs
an explanation of actual Session delays, not another workspace model ranking.
Inputs: existing explicit tutor requests; output: local, content-free stage timings.
No prompt, routing, output budget, grading, mastery, preparation trigger or model change.
No new paid calls/dependencies. UI behavior and mode/energy/sensory preferences unchanged.

## Verified current implementation
- `api/deps.py:get_repo` awaits `knowledge/reindex.py:build_repo` before the route body.
  `build_repo` unconditionally embeds `probe`. A timer inside `TutorTurn.run` excludes it.
- `orchestrator/tutor.py` computes existing latency before tutor trace/event/checkpoint
  and completed-answer writes. `/api/tutor.py` additionally persists the idempotency
  receipt before emitting done. Neither number is browser-visible completion time.
- Gateway already logs provider-attempt `first_token_ms`. Preserve its meaning and do
  not relabel it as browser paint or whole-request first text.
- Installed LiteLLM `llms/ollama/chat/transformation.py` constructs ModelResponseStream
  with choices and token usage only; native load/prompt/decode durations and cached
  prompt count are not copied. Absence must remain unknown, never zero.
- IndexState records dimensions and registry/version, but its current reindex update
  does not refresh dimensions/version fields. Before using this as a cache, verify
  identity, index compatibility and update semantics. A matching name alone is unsafe.

## Implementation order and acceptance
1. Add content-free, monotonic application phase diagnostics around Session preparation,
   retrieval, literal/semantic history, context rendering, first text, generation end
   and durable finalization. Include route dependency time and receipt persistence in
   the end-to-end harness; keep clock scopes explicit. Persist only bounded numeric
   diagnostics with existing learner-owned traces, or document a separately justified
   storage contract. Do not insert diagnostics into prompt sections or learning events.
2. Use fake providers and controlled clocks to prove delays are attributed correctly;
   verify errors, cancellation, partial output and idempotent replay. Replay must not
   claim a fresh inference. Ensure diagnostics cannot cause duplicate learning writes.
3. Measure HTTP headers, first nonempty SSE token and done via the real stream endpoint
   against disposable data with hosted disabled. Distinguish server delivery from
   browser paint. Start with bounded source-light/heavy and cold/prepared cases before
   scaling repetitions; quality review accompanies timing. Proposed report SLOs are
   unaccepted targets, not current guarantees. Small samples cannot establish <1% tails.
4. Native Ollama timings require a separate adapter slice. First test installed SDK
   extension points; do not replace streaming/accounting/termination behavior merely
   to expose metrics. Require compatibility tests and nullable validated native fields.
5. Preparation on direct entry, index dimension reuse and semantic-memory budgets each
   follow their own evidence/quality gate. Passive page mount is not automatically an
   explicit preparation action. Do not silently change the existing user-control policy.

## Remaining work
Initial planning/source audit completed before the implementation below. Existing timings
remain those in local-tutor-latency.md. No new model inference performed for this audit.
Implementation verification is recorded below; real-model measurements remain separate.

## First implementation: content-free server timing

Added request-scoped monotonic marks through pure ASGI middleware and ContextVar.
One `tutor_timing` JSON log entry contains schema version, HTTP status, completed-body
flag and cumulative elapsed milliseconds. No prompt, output, headers, source identifiers,
learner identifiers or URLs are included. It uses Uvicorn's configured INFO handler;
a default-server smoke emitted the record. There is no DB migration or new write in
learning transactions. This deliberately starts with local server logs rather than
adding telemetry columns before the useful measurement contract is established.
Logs follow the operator's normal stderr retention; they are not durable database traces.

Marks cover repository initialization when performed, dependency completion, turn start,
evidence/preference/experiment preparation, retrieval including its trace write, literal
history, optional semantic history including recheck, context, first nonempty text,
closed generation, answer finalization and done readiness. Response body completion is
recorded after ASGI send and excludes background jobs. These are cumulative server
milestones, not exclusive CPU times: backpressure/consumer scheduling can contribute.
Difference between neighboring boundaries supplies the corresponding elapsed segment.
No native load/prefill attribution or browser-paint claim is made. Missing stages remain
absent; replay has its own marker and never reports a new first model token. Errors can
have HTTP200 with stream_error; body_completed alone does not mean teaching succeeded.

35 focused tests pass: controlled-clock attribution, cancellation/context cleanup,
real orchestrator mark ordering and existing ownership/learning tests. Strict application
mypy passes228 files; targeted Ruff passes. Code review's normal-startup logging finding
was fixed and rechecked. 13 additional HTTP/replay tests pass, including partial and cross-transport replay
with unchanged inference count and learning writes (48 tests total).
No frontend changed; browser visual, keyboard and responsive checks are not new evidence
for this diagnostics-only slice. Previous Experiments browser checks remain separate.

Next: real HTTP measurement harness with disposable data, explicit cold/prepared cases
and source-heavy prompts; native Ollama telemetry remains a separately tested adapter
change. Do not call this a measured speedup or declare the latency problem resolved.
