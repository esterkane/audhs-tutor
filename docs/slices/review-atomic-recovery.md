# Atomic review-rating recovery

New model-free review and vocabulary ratings keep the intent claim, FSRS update, review log, events and completed response in one short SQLite write transaction. Failure or cancellation before commit rolls all of them back. Model-backed submissions retain their existing durable pre-inference claims; this change does not promise exactly-once inference.

A lookup reporting `not_found` means no saved rating is visible yet. An original request may still be running. The UI offers the original frozen identity and payload for resend; database serialization makes concurrent identical submissions wait or replay without duplicate learning evidence. A committed response lost in transit remains recoverable. Previously committed unresolved claims are never reclaimed automatically.

Content validation occurs under the write lock and again before learning writes. Session state is refreshed under that lock so a previously loaded open session cannot bypass a concurrent stop. There is no schema or backup format change, no new API, and no model-routing change.

## Verification

Full backend: 762 passed; frontend: 401 passed; lint, strict types and production build passed. Six isolated desktop/narrow browser journeys passed, covering content refresh, lost response after commit and retry before commit. Service tests cover cancellation and failures before commit, acknowledgement loss after commit, concurrent duplicates, legacy unresolved claims, session closure and final content guards. Tests use disposable data. Independent architecture and code reviews found no remaining major issues after session refresh and cancellation-test corrections.

## Remaining

Model-backed assessment requests still need an explicit distinction between provably unstarted work and uncertain inference. Broader R3, integrated learning acceptance and physical audio verification remain open.
