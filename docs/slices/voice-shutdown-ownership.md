# Voice shutdown retains database ownership

A disconnected or stopped voice connection must not close its database session while its child
response is still persisting traces, events or a durable reply. Interactive interruption retains
its existing 15-second admission timeout; that timeout is not completion of database cleanup.

The WebSocket route now owns its session with an explicit async context manager. After serving,
it closes the transport and drains the response task, then its final speaker reference, before
releasing the session. Drain shields children against cancellation of the socket owner, observes
task failures, and propagates owner cancellation after cleanup. A speaker created during a pending
claim is included. No new model calls, playback, event semantics, modes or learner controls.

This intentionally preserves ownership rather than force-cancelling SQLite work. Adapter timeouts
normally bound provider waits; a truly stuck in-process provider can delay shutdown. Hard process
termination can still leave durable requests unresolved. This is not an exactly-once guarantee or
a claim of bounded cleanup for arbitrary providers.

## Verification

Regression tests initially failed because shutdown was absent. They now cover cancelled owner,
late-created speaker, failed child observation and route order: transport close, child database
cleanup, database context exit. Full backend590 and lint/types passed; sanitized focused voice24
passed. Required code review found no blockers/majors. No UI or pedagogy behavior changed.
