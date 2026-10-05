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


## DL-01 follow-up: deterministic reproduction and bounded fix

The mounted-route timing gap is now reproduced in Review.test.tsx: a Suspense
boundary holds the Home transition while Review remains mounted, then the block
response arrives. Before the fix this renders the next lesson instead of Home.
This test models the vulnerable interval; it does not claim Home currently loads
through Suspense in production.

SessionControls now calls an optional pause callback before navigating. Review
increments a navigation-intent generation synchronously. Pending continue/finish
callbacks check their original generation as well as mounted state; a late response
can update authoritative cached progress but cannot take back navigation after Pause.
The finish path also stops further work after a paused, pending session read.
Generation rather than a permanently disabled flag allows a later explicit action.
No backend, curriculum, assessment, rating, mastery, audio or visual layout changes.

Original validation: 13 Review unit tests, 10 pause/clarity browser journeys,
TypeScript, lint and production build passed. The build retains existing chunk-size
and wavesurfer worker_threads warnings. Narrow resumed-review screenshot inspected;
keyboard pause, reload, persisted state and no-overflow checks pass at390/1280px.
Read-only code/control review found no blockers or majors.

DL-01's explicit Review Pause race is addressed. Header/Back navigation and the
analogous mounted-transition window on other screens are separate verification
items, not covered by this fix. DL-02, human comprehension, physical audio and the
rest of daily-learning acceptance remain open.

Sanitized variant: the same13 Review unit tests,9 pause browser journeys, TypeScript
and lint passed. Publication guard is required before its paired commit.


## Session Pause follow-up — start and next-block transitions

Two deterministic Session tests now expose the same mounted-route interval during
start and next-block responses. Both failed before the fix by showing Review after
Pause; both pass after the fix and verify cached committed state plus explicit resume.
A delayed Home fixture models the scheduling interval, not a production lazy route.

Session owns the pause guard above the block-keyed body. This matters because a late
response updates the cache and can mount a new body whose review/recap redirect would
otherwise bypass the old body's unmount check. Both async callbacks and that effect
now check the parent guard. The callback also binds to the route entry key; explicit
re-entry restores normal redirects without allowing an older entry's callback through.
No server progress is rolled back and no new learning write or provider call is added.

Original verification:10 Session unit tests,11 pause/Home browser journeys, lint,
TypeScript and production build pass. Existing build warnings remain; jsdom also
reports its existing unimplemented canvas context during the Session tests. The narrow
resumed-teaching screenshot was inspected; keyboard/reload and no-overflow checks pass.
Independent read-only review found no blockers/majors. General header/Back navigation
and session-ending callbacks are outside this bounded explicit-Pause fix.

Next: retain DL-02 as an open layout finding and continue the daily-learning matrix;
no whole UX or accessibility phase is closed by these race fixes.


## DL-03 — concept help after checked feedback, 2026-10-05

Before-change desktop/narrow browser journeys reproduced that both hint and concept-help controls disappear after grading. Revisit explanation exists, but requires leaving the checked question/feedback. This adds context-switching at the point a learner may be confused (S3 assistance gap); this is observed interface behavior, not an owner comprehension result.

A bounded fix now places optional “I don't understand yet — explain the idea” after feedback. It uses the same concept-and-similar-example prompt, skill and frozen question as pre-answer help. It does not claim to explain an individual mistake or regrade an answer. The new panel is outside the feedback live region, keyed by attempt, stops when inactive/unmounted, and does not count post-grade text as hints on the completed attempt. Continue, revisit and another-question actions remain.

Verified:12 affected component/Session tests; frontend lint/types/build; desktop correct-answer and390px incorrect-answer browser journeys, keyboard activation, help text, unchanged displayed feedback, zero additional assessment submissions, saved-feedback navigation/reload and no overflow. Screenshots inspected. Tutor streaming is mocked; no hosted calls or owner database changes. An initial browser run used a custom sandbox path unsupported by the fixture, then the standard disposable sandbox was used successfully. Independent code/pedagogy review found no actionable issue. Existing canvas/build warnings remain.

Remaining: this is concept help, not durable mistake-specific dialogue. Tailored feedback requires the original immutable submitted answer/criteria; current AttemptResult does not include that original answer and browser drafts are cleared after grading. Do not reconstruct it from a later draft. Review-card help after reveal, repeated-wrong-answer guidance, richer explanation controls, physical audio and owner comprehension remain open. DL-02 layout density remains visible in the narrow screenshot. No whole UX stage is complete.
