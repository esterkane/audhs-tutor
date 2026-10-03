# Review content versions (R3)

## Behavior

Review ratings describe recall of the exact card and answer shown. The server issues an opaque token over the owned review item's semantic fields, vocabulary meaning or referenced assessment/rubric, and rendered question/options/reveal. Scheduling fields are excluded: a changed due date is not changed subject matter.

New missing or stale content tokens fail before creating a request claim or changing FSRS. Completed original request identities replay their original schedule result, including versionless legacy identities. A second content check under the short SQLite write lock prevents a concurrent edit from changing what gets recorded. No model call is involved.

Both the main review queue and vocabulary practice keep the displayed card fixed until an explicit refresh. Refresh retrieves the same owned item, resets answer visibility and confidence, and requires a fresh rating. Original cards, options, revealed answers and attempted ratings are retained as separate browser archive entries until individually dismissed. Legacy single-entry archives are read without loss, and explicit page-memory fallback keeps already loaded entries. Assessment recovery uses the same retention behavior. Storage failure must retain the original pending record. Unknown outcomes remain unresolved rather than triggering another rating.

## Limits and compatibility

The shared process-bound HMAC signer lives in core; the deterministic review kernel does not depend on the tutor orchestrator. Restarting the backend requires a fresh card token for new ratings, but completed request replay remains durable. No schema migration, model routing or live content publication is part of this change.

This protects new ratings; it does not rewrite old learning evidence or define replacement/suspension policy for materially changed concepts. Those remain in R5. Recovery of unconfirmed interrupted requests remains separate.

## Verification

Verified 2026-10-03: full backend 757 tests and frontend 401 tests passed; lint/types and production build passed. All 86 Chromium browser journeys passed, followed by an eight-journey assessment/review rerun after archive refinements. Independent code and pedagogy review findings were addressed and rechecked. Acceptance covers vocabulary/reference/rubric changes, legacy replay, concurrent ratings, unchanged FSRS/event counts on rejection, explicit refresh and reveal, queue recovery, browser storage failures, and desktop/narrow browser journeys. Updated older browser setup helpers to supply the displayed assessment/review tokens rather than bypassing the public submission contract.
