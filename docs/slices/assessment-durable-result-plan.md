# Proposed next R3 slice: durable grade-result recovery

Status: implemented bounded grade-ready recovery (2026-10-04); interrupted inference without a saved grade remains unresolved.

Persist a dedicated assessment execution record keyed to the exact request claim. Use versioned request/content identity and validated result, with phases prepared → inference_started → grade_ready → completed. Commit inference_started before gateway entry; persist a validated result before applying learning evidence. Do not hold a database write lock during model calls or erase independently committed model accounting.

Offer explicit “Finish saving this result” for grade_ready. Under a short write lock, verify ownership, claim generation, content identity and phase; write attempt, events, competency, FSRS, checkpoint, completed response and phase atomically. Concurrent finish calls return the original outcome without a model call. Changed/deleted content retains the result for inspection but prevents applying evidence. Define ended-session handling explicitly before implementation.

An inference_started record without a saved result remains uncertain. External provider return and SQLite persistence cannot be atomic; never infer safety from elapsed time. Legacy claims without execution records remain unresolved.

Before migration, reconcile backup privacy: avoid duplicating hidden keys or corpus passages into learner-only backups, or explicitly redact those fields and mark recovery unavailable after restore. Required acceptance: disposable old-schema upgrade and backup/restore, failure at each boundary, commit acknowledgement loss, concurrent finish, changed/deleted content, ended sessions, learner isolation, preserved accounting and no inference on replay. This proposal does not close R3.


## Implemented contract and verification

Migration b834ef9026ac adds owner-scoped assessment_execution linked to the exact request claim. It stores original learner request, private stable content fingerprint and validated grade with aware original grading time. It does not duplicate source passages, hidden keys or full rubrics. Existing learner export/wipe and both backup scopes preserve these private response records; tests cover nonempty staged records and deletion.

Initial apply and explicit finish serialize on the claim and replay completed responses. Model accounting remains independent. Saved results can finish in ended owned sessions because this applies already graded work; new inference remains prohibited. Changed/deleted content prevents evidence application and retains the saved record. The frontend keeps the original request and offers Finish saving this result after lookup; no automatic regrading. Original timing is used for FSRS and evidence. Public content tokens still expire on restart; the private fingerprint permits recovery of unchanged content across token-key rotation.

Focused tests cover rollback, owner/session isolation, legacy migration preservation, content edits/deletion, process key rotation, ended sessions, concurrent finish and original-versus-finish race. Desktop/narrow keyboard journeys simulate grade-ready lookup and use the real finish endpoint to replay a completed result; backend failure injection separately proves actual grade-ready application. Independent backend and frontend reviews completed; timestamp and lock-cleanup findings fixed. No claim that absent saved output can recover interrupted inference. Read-only lookup also exposes the validated saved grade for a known grade-ready schema, even after source content changes or deletion. The recovery panel labels this feedback as progress not yet confirmed and supports local read-aloud; previewing does not apply evidence.


## Uncertain-result leave/return acceptance — 2026-10-12

Extended the existing desktop/narrow recovery journeys: expand the original answer
with the keyboard, Pause to Home, reload Home, Continue, explicitly check the saved
result and reopen the original answer. Assert identical answer text and server
session/checkpoint, no re-submit/continue-grading control, and exactly one original
submission. The only post during return is the existing local model-preparation
request; inspected its endpoint and scheduler, which do not grade or mutate checkpoints.
The first test expectation incorrectly rejected every POST; corrected to allow only
that exact owned-session preparation path, leaving all other writes forbidden.

All6 recovery journeys passed16.8s; targeted ESLint and e2e type checking passed.
No application behavior changed. The unresolved lookup is simulated after a real
committed deterministic attempt with delivery dropped, as in the existing test;
this proves presentation/re-entry behavior, not a newly interrupted inference
backend. Existing backend fault-injection evidence remains separate. Inference
without a persisted result remains uncertain; no automatic replay was added.
