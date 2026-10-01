# Voice request identities

Typed voice requests negotiate `typed-v1` in the ready message. Each explicit typed submission
gets a fresh UUID; response metadata, tokens, audio, errors and terminal messages carry that
identity. The client rejects late content and terminal messages belonging to another request.
Legacy clients and speech capture keep their existing protocol. No inference replay, automatic
resubmission, audio replay or learning evidence changes are introduced.

The server uses task-local context inherited by the response and speaker tasks, not a mutable
connection-global ID that could label old audio as a new reply. The receive loop resets its
context after admission. Invalid UUIDs are rejected before starting a turn. The identity is
correlation only; it is not yet a durable idempotency key.

Acceptance: typed content including audio shares one ID; a later legacy turn does not inherit
it; the browser ignores old/unidentified content during an identified request and accepts the
new matching response. Existing interruption/legacy behavior remains tested. Verification: backend580, frontend260, lint/types and production build passed. Real WebSocket tests use fake STT/TTS/model providers; client tests use fake sockets. Invalid IDs are rejected before a response; stale audio and final messages are ignored. Required reviews found no blockers or majors; reconnect now resets negotiation before handshake so startup errors stay visible, with a regression test. No paid calls or microphone capture.

Remaining: microphone utterance identity before capture, per-turn rejection/control identity,
durable terminal text lookup and explicit unresolved-request behavior. Provider-resistant
connection shutdown remains a lifecycle concern. No claim of full voice recovery or a passed
personal voice benchmark.
