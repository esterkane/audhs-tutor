# Approved synthetic hosted Glimmer trial

Scope: replay the eight reviewed synthetic app prompts against one pinned hosted
endpoint, recording first visible text, completion, truncation, billing and failures.
No live learner/course data, app assignments, kernel decisions, voice or UI changes.
This is a wire-level diagnostic, not end-to-end app latency or production integration.
The existing runtime diagnostic supplies the frozen prompts; production provider /
gateway integration remains a separate decision after evidence. No new dependency.

Execution: `uv run --project backend python scripts/eval_hosted_glimmer.py
--execute-approved-trial` from the repository. Reads only OPENROUTER_API_KEY from
process environment or local .env. No credential values or raw provider errors are
printed. The fixed journal is data/evals/glimmer-approved-20261012.sqlite3, ignored
by Git. Do not delete or duplicate it to restart the authorized campaign.

The SQLite reservation commits before sending. A pending request after interruption
halts the campaign, including after restart. Settled cases skip; no retries, repairs,
or fallback. Eight attempts maximum across executions. Unknown billing retains the
reservation and halts; excess billing records the actual cost and halts. Transaction
locking prevents concurrent reservations. This protects cooperative invocations from
accidental restarts, not deliberate database removal or a malicious provider.

Conservative reservation updated from the initial preflight: full131072 input plus
the advertised endpoint maximum16384 output, including reasoning, with5.5% overhead:
$0.062226432 per call, $0.497811456 for eight. Requests still cap output at900 for
comparison. Current endpoint prices and limits must exactly match before execution;
provider max_price also bounds unit prices. A token-cap breach halts the campaign.

Endpoint: OpenRouter meta/muse-glimmer-30b, deepinfra/bf16 only. Explicit provider
identity validation, parameter enforcement, no redirect, no environment proxy,
30-second transport timeout and90-second total call timeout. SSE comments are ignored;
reasoning is not counted as visible answer latency or saved as explanation text.
Usage cost is authoritative; reasoning/cache token details are recorded without
adding reasoning twice. Truncated/empty outputs remain failures for quality review.

Official contracts checked2026-10-12:
- https://openrouter.ai/docs/api_reference/overview
- https://openrouter.ai/docs/guides/routing/provider-selection
- https://openrouter.ai/docs/guides/best-practices/reasoning-tokens

## Verification and limits
Offline mock-transport and durable-journal tests cover restart, overlapping database
connections, eight-attempt exhaustion, no resend, missing usage/end marker, negative /
nonfinite cost, wrong provider, unsupported finish reason and price drift. These are
not network/provider or teaching-quality evidence. No browser tests: UI is unchanged.
Review and actual results to be recorded after completion; production stays local.

25 offline tests, Ruff and strict script mypy pass. Review found a possible
per-request surcharge gap: fixed by rejecting nonzero catalog request pricing and
sending max_price.request=0, with validation and transmitted-body regressions.
Second review found no remaining blockers/majors for this bounded diagnostic.

## Actual trial result — 2026-10-12
Eight calls completed with known reported cost; no retries. Five returned stop,
three returned length (two with no visible text). Total-response median over all
eight:4.91s; first-visible median over only the six nonempty outputs:3.72s. Empty
responses have null first-visible timing and must not be counted as fast answers.
First request took8.49s total/7.94s first visible. Single ordered samples do not
support p95, stable ranking or app end-to-end guarantees.

Reported cost totals $0.00834714; conservative5.5% overhead makes $0.00880623270,
less than one cent and below the $1 ceiling. Journal retains all eight settled
attempts so rerunning does not call the model again. No routing assignment changed.

Reasoning counts exceed completion totals in7/8 responses. Preserve reported cost
separately; never subtract these inconsistent counts to estimate visible tokens or
claim a reasoning fraction. Added an explicit parser warning and regression tests.
Final offline checks:27 tests, Ruff, strict script mypy pass.

Independent teaching review: arithmetic mostly correct in visible outputs, but
fractions answer omits requested percentages; fairness explanation uses unexplained
jargon; several replies add unnecessary exercises. Socratic visible question is
appropriate but length-limited. No fabricated citation/execution claims observed;
these fixtures do not test source-required grounding. Two empty answers fail the
basic teaching requirement. Do not promote this endpoint to production.

Artifact: evals/results/teaching-glimmer-openrouter-20261012.json, including exact
prompt hashes and case-level teaching review. Local completed-only median33.13s
versus hosted4.47s is descriptive, not controlled: BF16 versus local NVFP4, caching,
reasoning settings and transport differ. Both had5/8 completed responses at900 cap.
Next optional experiment should control reasoning/output allocation and evaluate
instruction following before considering any application integration. No additional
trial or paid calls are included in this slice.
