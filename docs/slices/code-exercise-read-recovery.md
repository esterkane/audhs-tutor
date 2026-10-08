# Code exercise read recovery

The session's optional code section and its editor both hid failed initial reads, including excluded-question responses. Existing exclusion controls would therefore strand a learner returning to a suspended code exercise. This slice makes that state recoverable before adding more mutation controls.

The exercise read now uses the existing cancellation/deadline helper. Failure shows the server reason, explicit Retry and Manage excluded questions. The session keeps the section mounted during loading/error. Observer remount retries are disabled to prevent the reproduced parent/child retry loop. Cached editor identity and saved code survive refresh failure. Successful retry focuses the workspace; failed retry keeps focus on Retry.

No new dependencies, model calls, scoring, eligibility, scheduling or mastery changes. A genuine missing-catalog 404 still means there is no optional exercise. Existing editing/run/submit controls remain unchanged.

## Evidence

The initial unavailable-exercise regression failed before the fix. Final focused component tests: 17 passed (exercise and session). Desktop1280/narrow390 isolated browser journeys verify the session entry, simulated excluded409, recovery link, keyboard Retry, focus and no horizontal overflow; screenshots inspected. Browser initially exposed the parent hiding failures and then the remount request loop; both were corrected. The request bound permits a cancelled/repeated initial development StrictMode read, not an automatic retry loop.

Frontend lint/types/build verified; existing bundle-size and jsdom canvas warnings remain. Bounded code/pedagogy review caught failed-retry focus movement; fixed and covered with cached-editor identity/focus assertions. Final review clear. Browser fixtures simulate failure and use the real sandbox API for recovery, with no paid inference or live DB change. Human comprehension and screen-reader acceptance are not claimed.

## Next

Explicit exclusion/restore controls inside code, challenge and listening activities remain open, including unsent-answer preservation and refresh after restoration. This read-recovery prerequisite does not complete R5 or those controls.
