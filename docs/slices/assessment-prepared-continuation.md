# Explicit prepared assessment continuation

Implemented2026-10-08; bounded R3 recovery, not resolution of unknown model outcomes.

## Problem and scope
After a process exits before inference, an owned prepared submission previously only offered repeated result checks. Real existing desktop/narrow recovery journeys passed before this change; no explicit continuation existed. Original claim/answer must survive and ordinary submit must remain blocked.

## Implementation
GET result checks may now report prepared_ready only after reacquiring the exact original unlocked, unsealed external guard and transactionally rechecking generation/phase/receipt, immutable payload fingerprint, active owned session and unchanged private content fingerprint. Legacy, restored, missing, held, sealed or malformed proof remains unresolved. A changed/deleted question or ended session cannot start inference. Public content tokens can rotate across processes; only stable private equality permits a refreshed in-memory token. Durable original request data is never rewritten.

POST /api/assess/requests/{id}/continue is explicit. It holds the same guard through the existing grader, skips duplicate prepared-row creation, seals before each gateway entry and preserves original identity on every failure. Completed calls replay the original result; ordinary submit still returns409 for unresolved identities. No startup generation, time-based reclaim, model change, scoring change or automatic resend.

The recovery panel offers Continue saved submission only after the eligible check and explains that the original answer is graded while current edits stay separate. Double submissions are blocked; uncertainty clears displayed eligibility and requires checking again. Operational errors no longer show the unrelated storage-corruption acknowledgement. Existing grade-ready finish, feedback reuse, stop/change-topic and original-answer controls remain.

## Evidence
-40 distinct backend checks pass across continuation, request/execution, lifecycle and real process-exit tests. A new model-boundary check additionally verifies that continuation seals before gateway entry and cannot repeat after acknowledgement loss. Exact logs: /tmp/assessment-continue-backend.log (39) and /tmp/assessment-continue-model.log (12, including11 overlapping cases).
-24 UI tests pass; six isolated Chromium journeys pass for desktop/narrow staged recovery and content-version behavior. Lookup presentations are simulated in these browser checks; actual eligibility, hard process exits and writes are verified in backend tests. Tab/Enter reaches and activates continuation; no horizontal overflow. Desktop/narrow recovery screenshots were visually inspected: /tmp/assessment-continue-{desktop,narrow}.png.
-Ruff, full backend mypy204files, frontend lint/type-check/build pass. Production build retains its existing chunk-size warning. Independent bounded code/copy review found no blockers or majors.
-The idle non-reloading live backend was gracefully restarted after a verified SQLite recovery snapshot. Health200, endpoint presence and migration f628a4d31c90/owner_json verified on the actual installation. No live learner submission was generated for testing.

## Remaining
Lost results after inference starts remain unresolved; this deliberately cannot infer provider completion. Whole-filesystem rollback including guard files remains outside ownership proof. Human comprehension, screen-reader/physical-audio acceptance and wider R3 workflows remain open. Next reconcile remaining R3 uncertain-outcome handling and R4 content/draft conflicts rather than widening automatic retries.
