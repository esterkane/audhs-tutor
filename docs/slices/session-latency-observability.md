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


## Real loopback HTTP check — 2026-10-12
Three bounded local calls used disposable SQLite and the actual Session SSE endpoint;
seeded curriculum with deterministic in-memory retrieval (not production Qdrant). No
hosted providers, live learner writes, model unloads or prompt/routing changes. Initial
two replies: first text9.987/9.734s, done16.630/16.519s. Migration logging disabled the
new child logger; fixed Alembic fileConfig to preserve existing loggers. A subprocess
regression proves actual stderr after Uvicorn configuration followed by real migration.
Three focused timing tests and Ruff pass; bounded code review found no remaining issue.

Final profiled turn with Gemma already resident: first text9.896s, done16.169s. Context
ready42ms, server first text9894ms, generation closed16159ms, answer finalized16167ms,
body sent16168ms. This fixture concentrates delay in model processing/generation; it
does not prove production retrieval is always cheap or native load is zero. Arithmetic
was correct but the explanation overgeneralizes alignment without fixing magnitudes;
not a teaching-quality pass. No more samples needed to answer this narrow hypothesis.
Evidence: evals/results/session-http-profile-20261012.json. Next: native model phase
metrics; avoid reducing history/retrieval budgets based on this synthetic fixture.


## Native timing experiment — 2026-10-12
A temporary in-process wrapper observed numeric fields before the installed LiteLLM
parser discarded them; original parsing and requests were unchanged. Two disposable
Session HTTP calls used deterministic seeded retrieval, no hosted model or live data.
Repeated prompt:2638 input tokens,2637 reported cached; load0.0048s, prompt0.1518s,
generation6.1115s for169 tokens, stop. Changed question:2607 input tokens,0 cached;
load0.0045s, prompt9.6737s, generation6.9074s for190 tokens, length/partial. This confirms
uncached prompt processing dominated that changed-question wait; it does not explain
cache invalidation or establish production percentiles. Evidence:session-native-profile-20261012.json
in evals/results. The observer remains temporary, not a production SDK monkey patch.

Next hypothesis: identify which rendered sections account for uncached input using
existing token estimates and exact prompt-prefix comparison, without new inference.
Only then choose a bounded quality-tested optimization. Do not lower output limits:
the changed question already terminated partial. Do not remove sources or reintroduce
rejected reordering as an assumed safe speedup. Native telemetry remains diagnostic
only; permanent adapter support is not yet implemented. Batch this evidence with the
next implementation publication rather than issuing another status-only commit.


## Offline prompt comparison — 2026-10-12
Reconstructed both requests through production Session assembly with fake generation
and separate disposable databases; no new inference. System content is byte-identical
(3151 characters); user messages share3010 initial characters and first differ inside
retrieved knowledge. No early timestamp/ID volatility was found in this fixture.
Approximate section costs: policy787, retrieved1369/1302, output contract420, learning
contract170, state37, evidence35; estimates are not native tokenizer counts. Evidence:
evals/results/session-prompt-comparison-20261012.json. This weakens a generic early-field
reorder hypothesis: substantial shared prefix already exists. Next inspect runner
cache reuse/rollback semantics before changing educational content. Do not infer that
retrieval is unnecessary from its size. Official cached-count definition verified at
https://github.com/ollama/ollama/blob/main/docs/api/usage.mdx (read2026-10-12); installed
v0.33.3 reports cached input count independently of logical total input.


## Runtime cache cause and bounded candidate — 2026-10-12
Installed runner log for the2607-token changed request explicitly forces full prompt
reprocessing because retained SWA checkpoints cannot restore the required prefix. The
normal process is llama-server with32768 context; installed --help exposes --swa-full
via LLAMA_ARG_SWA_FULL. Ollama v0.33.3 llm/llama_server.go inherits os.Environ.
This establishes a concrete runtime candidate without changing educational context.

An isolated server with LLAMA_ARG_SWA_FULL=1 confirmed full SWA allocation in logs:
2048MiB non-SWA plus10240MiB SWA. First/cold request took15.88s to first text with5.97s
load. Changed request reused1477/2607 tokens: prompt4.267s, first text4.283s, total11.236s;
baseline changed request had0 cached, prompt9.674s, first9.782s,total16.706s. These are
individual observations, not p95 or an isolated randomized effect estimate. Temperature,
context, prompt and output cap retained. Both changed answers end partway through a
numerical example at190 tokens. Neither is teaching acceptance; do not conceal partial
output to claim a speedup. Original runtime untouched; isolated server shut down.
Evidence:evals/results/session-full-swa-20261012.json.

Next bounded implementation should expose a reversible opt-in local runtime profile
with explicit memory cost and independent port, then compare multiple representative
Session turns and complete-answer quality before adoption. Output-cap adequacy is a
separate observed teaching issue, not permission to lower the budget further. No global
launch environment, model route or owner daemon was changed. Batch these measurements
with that implementation rather than repeatedly publishing investigation-only commits.


## Opt-in launcher implementation
`scripts/local_tutor_runtime.py` provides a separate loopback runtime with explicit
--full-cache, --check, independent port, compatible-runner check and owned-process
cleanup. It allows two resident models so embedding does not systematically evict the
tutor. No automatic app switch or permanent environment edit. Four tests, Ruff and
strict script mypy pass. Actual installed --check succeeds; live launcher returned
/api/version200, Ctrl-C exited130 and its port closed. Review found SIGTERM cleanup
gap, now fixed with regression and re-review. No browser UI changed; no new visual
claims. Usage/rollback/memory limits:docs/LOCAL-TUTOR-RUNTIME.md. Performance/quality
acceptance remains open; the full-cache profile is experimental, not default.
