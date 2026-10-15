# Owned checkpoint saves and session details

Three baseline HTTP tests failed: foreign session detail and checkpoint requests succeeded, and a completed session accepted a checkpoint write. Session detail now uses the existing owned lookup. Checkpoint saving uses the current learner and `open_transition`, reads/validates/merges under the shared SQLite writer lock, and defers its save to that transaction. Foreign/missing requests share 404; completed writes return `session_ended` 409.

No UI, schema, payload, allowed-phase, reserved-key, grading or scheduling change. Existing owner checkpoint behavior is retained; this does not add a new learning decision.

## Verification

- Ten focused cases cover foreign/missing equivalence with whole-DB no-write assertions, post-Finish rejection, both checkpoint/Finish and checkpoint/advance orderings, staged error/cancellation and final commit failure.
- 68 affected backend tests pass, including ordinary checkpoint phase/reserved-key/optional-index behavior, block ownership and lifecycle transactions.
- Code and pedagogy source reviews found no blockers/majors.
- Full lint/types pass.16 isolated browser pause/resume, Back/Forward, late/uncertain transition and stop/navigation scenarios pass with desktop/390px and keyboard checks. Narrow resumed lesson screenshot inspected; no UI code changed. Dedicated test database/ports used, no learner database or paid calls.
- Sanitized checkout:24 affected backend tests pass.

## Remaining scope

Internal tutor checkpoint writers, adaptation acceptance/undo and same-block semantic request ordering are not certified by this API boundary. Next review the adaptation lifecycle before returning to broader integrated daily-learning acceptance. Human comprehension, physical audio and screen-reader acceptance remain open.
