# Reversible saved-thought actions

## Problem and current evidence — 2026-10-04

Remove explicitly offers no undo. Promotion changes status/promoted_to and can also change node_id; removal sets status=dropped and commits without an event. Neither endpoint has a revision guard. Client timeouts correctly state that the server may have applied the action, but a retry has no action identity. Restoring a browser-held snapshot is therefore unsafe: another tab may have subsequently changed the thought. Original_context_json must remain immutable.

Inspected parking.py, ParkingLotItem, parking/api.ts and ParkedList.tsx. Four existing saved-thought browser journeys pass: failure retention, confirmation/Keep focus at390/1280, actual Home destination, and timeout with no duplicate or automatic submissions. This is baseline evidence, not undo implementation.

## Required transaction contract

- Add a monotonically increasing item revision, initially zero. Every state-changing action path, including legacy promote/drop calls, increments it. Legacy clients remain usable but cannot bypass revision tracking.
- Add a learner-scoped action receipt with unique request identity, canonical payload fingerprint, item ID, before/after reminder state, resulting revision and optional undo-of reference. Store status, promoted_to and node_id snapshots; do not copy source text or overwrite original_context_json, created_at, text or learning evidence.
- New action requests carry expected revision and request identity. Same identity/same payload returns the receipt/current item without another write; differing payload conflicts. Distinguish the recorded outcome from the current item if later actions have occurred.
- Acquire the SQLite write transaction before checking/updating the guarded revision, or use an atomic conditional update. Item change, receipt and audit event commit together. Failed audit/receipt writes roll back all state changes. No model/network call inside this transaction.
- Undo names a server receipt, never a client-supplied previous state. It is allowed only for the current latest action/revision belonging to this learner/item. A stale undo returns conflict plus a refresh path; it never silently overwrites newer work. Undo itself is a recorded revisioned action with retry identity. Do not expose redo or undo-of-undo in this slice.
- If restoring a previous skill link is no longer valid, explain the conflict instead of choosing a substitute. Removed thoughts remain retained records; this is recovery from hiding, not permanent deletion.

## UI slice

Keep existing confirmation and Keep focus until undo is proven. After confirmed Show on Home or Remove, expose a labeled Undo action and state what it restores. Keep it available without a countdown until another action supersedes it or the view is left; durable receipts support future history without promising that UI now. Bound mutation waits, disable duplicate submission, refresh on uncertainty, and never issue automatic retries. Retain request identity for explicit retry of an unconfirmed action. On conflict, keep the refreshed newer state and explain why undo could not apply. Focus feedback only if the learner has not moved elsewhere.

Preserve all original material links, draft capture and saved-thought list capabilities. Show on Home and removal remain reminder organization, never curriculum selection or completion evidence. No new dependency or hosted service.

## Bounded implementation order

1. Backend migration/model, typed request/receipt, atomic revisioned service and compatibility paths; generated API types. Prove replay, race and rollback before UI adoption.
2. Existing action hook/list uses guarded actions and explicit Undo. Preserve independent capture-save request keys. Update confirmation wording only with functioning recovery.
3. Browser recovery and keyboard/narrow verification, handoff, private snapshot and sanitized publication.

Likely files: db/models.py, new migration, schemas or api/parking.py, a focused service if needed, db/events.py/event schema docs, parking/api.ts, ParkedList.tsx, generated api-types.ts, backend action/migration tests and saved-thought-actions.spec.ts. Avoid broad mutation-framework refactors.

## Acceptance

- Remove parked/promoted item then undo restores exact prior reminder/link state and unchanged original source.
- Promotion then undo restores parked state and original node_id.
- Concurrent same-key actions yield one receipt/event/revision; changed payload conflicts.
- Different actions sharing an expected revision: one succeeds, the other conflicts.
- Lost successful response and explicit retry do not repeat action/event; no silent replay after newer state.
- Late/stale undo after another tab changes the item cannot restore older state.
- Ownership, missing linked skill, event failure and migration upgrade/downgrade preserve invariants.
- Keyboard focus, slow/error/conflict feedback, narrow layout and refreshed Home/Saved thoughts agree with server state.

C6 remains open until implementation and verification. C7 typed recents follows; human acceptance remains separate.
