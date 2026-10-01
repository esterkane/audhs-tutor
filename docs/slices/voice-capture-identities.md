# Microphone capture identities

Negotiate utterance-v1 on connection. Before opening the microphone, each explicit Talk action
sends a fresh capture UUID. Matching listening/processing/transcript/token/audio/terminal events
carry that identity. A processing boundary closes browser capture, including a late permission
resolution. The server accepts no further binary frames until a new explicit capture request;
late end-of-speech controls cannot start another transcription. Typed turns invalidate any old
capture buffer. Legacy protocol clients remain supported.

Only matching speech content updates the current response; stale events are ignored. No raw
audio persistence, automatic recording/reconnect/retry, model rerouting or learning-evidence
adaptation is added. This is correlation and bounded capture, not durable request replay.

Acceptance: fake-provider WebSocket speech events carry the capture ID, late frames/control do
not make a second STT call, subsequent typed response has its own ID; browser hook stops the
microphone only for matching processing and ignores late PCM callbacks. Existing legacy voice
and interruption suites must remain green. Verified: backend581/frontend261, lint/types and production build. Required code and pedagogy reviews found no blockers or majors. Fake providers/microphone only; no live capture or paid calls.

Remaining: identity-bearing control acknowledgements, durable terminal status lookup and
explicit unresolved-request UX, provider-resistant teardown, real personal voice benchmark.
