# Atomic session finish including cleanup

## Reproduced problem

Failure injection immediately before recap persistence left the session open while its current block/checkpoint was already ended. This extended the known transaction gap in session-end-atomic.md. The test failed before the fix with running→ended checkpoint drift.

## Implementation

The API verifies ownership, acquires a learner-scoped SQLite writer lock using a no-op session update, then stages recall creation, running-block event/checkpoint and old-checkpoint pruning without intermediate commits. Existing kernel end commits these with the first session completion and matching recap. Errors and cancellation before that commit roll everything back. Independent workers refresh after acquiring the lock; already-ended retries skip cleanup and retain the first recap.

Standalone helper defaults still commit. Event order, eligible recall selection, FSRS calculation and stop eligibility are unchanged. No schema migration, frontend change, model call or provider routing change. See ../design/SESSION-END-TRANSACTION.md.

## Verification

- 55 affected backend tests pass. Eight new cases include the original checkpoint regression, six failures/cancellation across preparation/recap/commit, and independent concurrent finish workers bypassing the process-local request lock.
- Failure tests compare every persisted table before/after; retry creates one recall/memory pair, one block-end event and one completion event, and prunes only old checkpoints. Repeated end leaves the snapshot unchanged.
- Cancellation is tested directly at the API handler with its own database session because ASGI middleware converts cancellation to a no-response exception.
- Six real-sandbox browser scenarios pass: lost recap response, competing finish controls and delayed end response after navigation, including narrow/desktop and keyboard paths. Narrow navigation screenshot inspected. No live learner writes or paid inference.
- Full lint/types pass. Independent code and pedagogy reviews found no blocker/major. Added the code reviewer’s explicit event-order assertion and reran all eight new cases.

## Limits

Response assembly and exact-recap confirmation happen after commit. A lost response still needs the existing completion receipt and retained local draft; no automatic resubmission. This does not make all block transitions or all session mutations one global transaction. Existing historical partial states are not silently rewritten. Human comprehension and physical audio gates remain open.

Concurrency coverage is for competing finish workers. Other concurrent lifecycle mutations (block start/advance) are not certified by this change.
