# Browser review recovery

Story: a learner whose review reply is lost can check the original rating, then continue without
rating the same card twice. Review and vocabulary use the owned backend request API from the
review-request-recovery slice. Browser storage holds temporary intent/queue checkpoints, never mastery.
No new schema, learning event, model call or sensory/mode change. Optional confidence remains optional.

## Behavior and acceptance evidence

- Persist UUID, session, item, original rating/help/confidence/timing and visible question before POST.
- Bound requests to 15 seconds and fence late responses after unmount/session change. No automatic resend.
- Lookup is read-only; not-found offers explicit resend of the same identity/body. Completed ratings
  load the current queue while describing the original schedule as historical.
- Keep confirmed intent until queue checkpoint succeeds. Failed checkpoint survives remount; acknowledgement
  cannot erase a newer intent. Storage errors alone offer explicit page-memory fallback with reload limits.
- Advance by stable item ID, including vocabulary; clear confirmed-card help and reset confidence/timing.
- Stop/change activity stays available; recovery controls have accessible names and status/error text.

Verification: full frontend suite 305 tests / 80 files; two isolated desktop/narrow Playwright
review-recovery journeys; ESLint and production build passed. Focused tests cover lost response,
remount, exact resend, denied/malformed storage, queue checkpoint failure, stale acknowledgement,
timeout, session change and confidence/timing reset. Browser tests use disposable sandbox data.
Backend code is unchanged from the separately verified request foundation.

Review fixes: code review found queue durability and storage/network-error conflation; pedagogy
review found inherited confidence/timing and premature saved-rating wording. All addressed and both
reviews cleared. No live learner ratings or paid models used for verification.

Limits: page-memory mode is not reload-safe; pre-commit unresolved requests cannot be automatically
regraded; legacy unkeyed clients and content-version guards remain separate. No claim that R3 is complete.
