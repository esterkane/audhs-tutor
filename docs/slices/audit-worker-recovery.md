# Audit R2a — code-worker failure and cleanup (F11)

Story: a runtime crash must show an immediate crash result, and leaving code practice must settle outstanding work. Inputs: worker ready/error/result, timeout and dispose. Outputs: settled load/run promise and reusable runner after cleanup. No learner events, grading, model requests or state schema changes. Existing error UI and opt-in code execution are retained.

Reproduced with a fake worker emitting error during run: prior code returned timedOut=true. Added error listener and unified run finish/cleanup for success, crash, timeout, dispose and postMessage failure. Crashed/timed-out workers are discarded. Disposal rejects pending loading and settles running code; generation guard prevents resuming a run after dispose. Concurrent runs are rejected rather than sharing uncorrelated worker responses.

Five deterministic runner tests cover load failure/retry, run crash, loading disposal, active disposal/concurrent invocation, and timeout/fresh-worker retry. Full frontend/lint and review results are recorded in HANDOFF. These fake-worker checks do not establish hostile-code isolation or real-device performance.

Related R1 browser evidence: added audit-selection.spec.ts tests against real sandbox Vite/FastAPI/SQLite, with/without current session, keep-current then replace, reload and server checkpoint assertions. Existing session-journeys updated for accurate completion wording. All five selected browser journeys passed; no live learner database or paid providers used. R1 Show-all race is covered by component tests, not an added real-backend race journey.

No new dependency, API or schema change. Remaining R2 issues include stream request identity, general errors, model route reset, voice transport and parking saves. Owner comprehension and broader browser/accessibility coverage remain separate.
