# Voice interruption control identities

A delayed interrupt must not stop a newer request. The server records the currently admitted
request independently from the capture buffer, rejects mismatched controls, and tags the
interruption acknowledgement with that request ID. Clients negotiate control identity support
and ignore old or missing acknowledgements when it is enabled. Both matching acknowledgement
and terminal completion are still required before sending the next request.

Stop voice continues to close the whole connection immediately; it is not scoped to one reply.
Legacy interruption remains supported without silently requiring a new client protocol. No
automatic retry, inference replay, audio playback, learner evidence or preference adaptation.
This remains correlation, not a durable exactly-once guarantee.

Acceptance: stale/missing controls cannot reach server interruption; one matching control gets
one matching acknowledgement; stale/missing client acknowledgements cannot unlock a stopped
turn. Existing legacy, capture and typed suites stay green. Verified: backend582/frontend262, lint/types and production build passed. Fake-provider WebSocket checks plus client/server regressions cover stale/missing and matching controls. Required code and pedagogy reviews found no blockers or majors. No paid calls or physical microphone capture.

Next: durable voice terminal lookup and explicit unresolved-request recovery, plus provider-
resistant connection teardown. Personal voice benchmark remains open.
