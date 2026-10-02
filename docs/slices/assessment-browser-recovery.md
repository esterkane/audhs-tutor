# Browser assessment recovery

The learner can recover feedback after a lost response without silently grading again.
Session, challenge, listening and code assessments freeze request identity and payload before POST.
Result lookup reads server state; only explicit not-found resend uses the same key and body.
No new learning events or model calls on lookup; grading events stay backend-owned.
Mode/energy behavior is unchanged. Keyboard-accessible recovery and opt-in read-aloud are available.

## Implemented
- Session-scoped pending identity in sessionStorage; normal submission is blocked until resolved.
- Fifteen-second bound, abort and scope/operation checks reject stale asynchronous completion.
- Original question and human-readable answer accompany the frozen body.
- Completed results may be explicitly adopted only when current assessment and answer match.
- Stop/change topic remain available; unresolved requests cannot silently regrade.
- Storage failures do not create a permanent dead end: acknowledged page-memory mode preserves the
  latest readable identity. Its warning explains lost recovery on reload and possible prior grading.

## Verification
- Frontend suite: 293 tests across 79 files passed.
- Hook regressions cover lost response, remount, exact resend, denied get/set/remove, malformed
  storage, page-memory recovery, abort-resistant timeout, session switch and newer pending identity.
- Isolated desktop/narrow Playwright journeys: 2 passed. Real sandbox grading commits before the
  browser response is aborted; reload and keyboard lookup recover feedback with only one POST.
- Frontend lint, TypeScript and production build passed (existing bundle-size advisory remains).
- Required code and pedagogy reviews cleared blockers/majors after adding memory fallback and readable
  original MCQ/code answers. No live model, live learner database or paid provider used in tests.

## Limits / next
The backend still does not make all grading writes one transaction. Unresolved claims remain honest
uncertainty, not proof of failure. Legacy unkeyed API clients are not protected. Browser recovery is
per session/tab and does not survive clearing storage; memory fallback lasts only this page lifetime.
Current-work adoption checks item ID and answer, not a content-version hash; content-edit conflicts
need a separate end-to-end guard. Review-rating idempotency and broader R3 gates remain open.
