# Daily learning acceptance — 2026-10-05

## Scope and result

Read-only acceptance pass at original commit `9011c91`. No runtime, learning logic,
model routing, schema or styling changes. All tests use a disposable sandbox with
hosted providers disabled; none establishes model quality or owner comprehension.

Initial six-file batch: 16 passed, one failed. The failure was the late review-next
response test: after Pause returned the URL to Home, the expected Continue button
was absent and the captured page showed the next lesson. Treat this as an open,
intermittent navigation/recovery finding, not a fixed defect or a proven flaky test.

Three isolated repetitions of that exact test passed. The complete original batch
then passed all 17 tests. Six additional recovery tests passed. Passing reruns do
not erase the initial failure. Existing Review callbacks check an active ref cleared
on unmount; whether route commit/cleanup timing explains the failure is unproven.
No speculative navigation patch was applied.

## Evidence matrix

| Journey | Evidence | Limit |
|---|---|---|
| Choose topic with an existing session | home-session-intent: 2 passing, desktop/narrow | No owner comprehension claim |
| Lesson → code workspace → return | lesson-playground: 2 passing | Synthetic tutor response; real browser workspace |
| Hints, optional confidence, labels, topic change | session-clarity: 1 passing | Does not evaluate grading quality |
| Pause and restore teach/assess/review | session-pause: 6 passing at 1280/390 | Keyboard pause, reload and persisted state checked |
| Delayed block response after pause | session-pause: 3 passing on rerun | Review-next failed in initial batch; unresolved |
| Starter load timeout and retry | task-notebook-recovery: 2 passing | Synthetic source files; notes preserved |
| Notebook execution and checked return | task-notebook: 1 passing | Real local browser execution of a small fixture, not full scientific notebooks |
| Partial explanation, reload, explicit original retry | lesson-recovery: 2 passing | Synthetic streaming/replay; request identity retained |
| Return to original lesson after checkpoint moves | recent-lesson: 2 passing | Explicit choice; no automatic session writes |
| Failed session read, keyboard retry/Home | session-loading: 2 passing | Injected HTTP failure |

Commands use `SANDBOX_API_PORT=8011 SANDBOX_UI_PORT=5175`, separate disposable
`SANDBOX_DB` files and `LITELLM_LOCAL_MODEL_COST_MAP=True` with
`pnpm --dir frontend exec playwright test` and the named e2e files above.

## Visual findings and outstanding gates

Inspected the 390px resumed-teaching screenshot and the 1280px recovered task
notebook screenshot. Controls and content wrap without horizontal overflow in
these journeys; keyboard pause/retry/original-lesson actions are exercised.

- **DL-01, provisional S3:** intermittent delayed review transition can apparently
  reclaim navigation after Pause. Preserve the initial evidence in this record.
  Next: instrument navigation timing or make a deterministic reproduction before
  changing code. Any fix must preserve server-committed progress and explicit resume.
- **DL-02, S2:** at 390px, header, session controls and secondary tools place the
  explanation below the first 900px viewport. The exit controls are reachable, but
  the current learning action competes with secondary choices. Minimal candidate:
  retain visible pause/current topic and progressively disclose secondary controls.
  Longer term: apply the authoritative lesson workspace composition. Test focus,
  discoverability, saved-state feedback and all retained controls before adoption;
  do not remove functionality or alter learning decisions.
- The desktop notebook shows starter code, preceding instructions, prediction,
  tutor focus and checked-return controls. The page remains long; this is not proof
  that an unfamiliar learner understands its sequence.
- Real browser zoom, screen reader, physical headphone output, learner comprehension,
  repeated incorrect answers, real slow-model recovery and delayed learning transfer
  remain open. No whole-stage acceptance is claimed.

Lint/type/build were not repeated because this pass changes documentation only.
Next bounded work is DL-01 reproduction, then the remaining failure/learning matrix.
