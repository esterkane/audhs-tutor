# Shared retrieval initialization

Concurrent cold HTTP and voice requests must share the app's retrieval repository.
Inputs remain the existing app, request DB and settings; output is the unchanged
RetrievalRepository. No new events, prompts, learning policy or UI. Mode, energy,
keyboard and responsive behavior are unchanged; no browser presentation change.

## Reproduction and implementation
A controlled concurrent dependency test failed before the fix: build_repo ran twice.
An app-owned asyncio lock now serializes initialization, rechecks after waiting, and
publishes only a completed repository. Failures and cancellation release the lock;
a waiting request can retry using its own DB session. Ready instances bypass the lock.
HTTP and voice use the same helper, preserving the voice test factory's loop affinity.
No persisted dimension cache is trusted or embedding probe removed. This prevents
duplicate startup work, not the measured model prefill/decode delay. Initialization
itself can still fail; callers retain existing failure behavior.

## Verification
22 focused tests passed: test_repository_initialization.py, test_voice.py,
test_tutor_timing.py. Includes concurrent first requests, builder failure/cancellation,
retry and factory sharing, plus existing WebSocket flows. Ruff and strict app mypy228
passed. No UI, source selection, prompt budget, learning evidence or default runtime
changes. No latency percentile claim. Bounded code review found no blocker or major issues.

Recent local runtime diagnostics remain in session-latency-observability.md. Full-SWA
remains optional; more frequent standard-SWA checkpoints did not preserve reuse.
