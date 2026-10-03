# Review request recovery foundation (R3 / F04)

A lost response or retry must not review the same card twice. Review due/rating/lookup require owned
sessions; item ownership is checked before a claim. Optional UUID identities bind item, session,
raw rating/hints/confidence/latency and explicit benchmark time to one logical request.
FSRS card/log, reviewed event and outcome commit together. Lookup is read-only; no model calls.
Assisted-recall rating caps, optional confidence, mode/energy caps and visible controls remain unchanged.

## Implementation
Namespaced review claims use the existing learner-scoped durable request table. Equal completed retries
return the original schedule, conflicting payloads return 409, and unresolved claims cannot repeat.
A short SQLite write lock is acquired before reading the card, preventing concurrent distinct ratings
from calculating from one stale card state. Real review time is taken after acquiring that lock.
Legacy unkeyed clients remain accepted; all rating learning writes are atomic regardless of key.

## Verification
Before-fix tests reproduced duplicate scheduling and foreign-session 200 responses on due and rating.
Tests cover exact replay, hint cap, payload conflict, owner checks, fresh connection/ended-session replay,
read-only scoped lookup, concurrent equal requests and rollback of card/log/event/outcome.
Full backend643 passed; final expanded request tests8 passed, including different-key concurrent ratings reading successive card states. API generation and lint/types passed. Required code and pedagogy reviews cleared blockers/majors; the extra concurrency case addresses the code-review verification minor.

## Next / limits
Browser review surfaces still need UUID/frozen-body persistence, explicit lookup and queue reconciliation.
Do not mark R3 complete. Pre-commit interrupted claims stay unresolved; no automatic resubmission. Existing
unkeyed browser behavior is not yet protected against lost-response retries. No migration/dependency or
live data/model changes; archived request outcomes remain historical, not the current review schedule.
