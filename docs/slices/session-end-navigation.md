# Session End navigation ownership — AU-SESSION-04

## Reproduced problem
At390/1280 in a disposable sandbox, End committed on the server while its response was delayed. Navigating to Preferences then releasing the response redirected the learner Home. Both pre-fix browser regressions failed. A mounted-only guard was insufficient; browser history must also retain the initiating entry.

## Change
useStopSession captures the ended session ID and browser history key/URL at mutation start. Completion only navigates if the originating view/session still owns that history entry and no Back/Forward event intervened. Listeners are cleaned on settlement or unmount/session change. Store and current-session cache are cleared only when they refer to the ended session; server queries are invalidated for reconciliation. A newer session's selected skill is retained.

No backend, grading, scheduling, completion or assessment logic changed. End still commits after navigation; leaving does not cancel the server operation. No new library, model request, design token or layout change.

## Evidence
- Six component tests pass: normal End, Pause, delayed End after leaving, newer session preservation, history change before unmount, Back/Forward invalidation with unchanged entry.
-16 browser scenarios pass against real sandbox API: two new delayed-End desktop/narrow cases plus14 existing Pause/checkpoint, late transition, Back/Forward and lost-response cases. Preferences link operated with keyboard. No document overflow at390/1280; resulting screenshots inspected.
- Full lint/type checks and production build pass; existing bundle-size warning remains.
- Code review identified history timing gap in initial solution; corrected and re-reviewed with no blockers/majors. Pedagogy review found no blockers/majors.
- Logs: /tmp/session-stop-{before,after,unit,lint,build}.log. Browser screenshots in frontend/test-results/session-stop-navigation-*/preferences-after-end.png (ignored).

## Remaining scope
This does not implement an End-request timeout, cancellation or all cross-surface draft recovery. Human accessibility/audio acceptance remains open. No claim of a complete R4 stage.
