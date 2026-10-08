# Code-question practice controls

Primary code assessments now reuse the explicit question exclusion/restore controls. The editor and local Run remain available while excluded; new code submissions, hints and solution requests are disabled after the acknowledged change. The linked explain-back is a separate assessment and remains unchanged in this slice.

Restoration does not silently resume grading: the learner explicitly refreshes the same canonical exercise, then runs the code again against its fresh checks. Refresh has a bounded deadline, cancellation on unmount and duplicate-request guard. Failed refresh preserves the code and earlier results; successful refresh clears stale run results and focuses the practice panel. Code, explain-back draft, hints and solution exposure are retained. Exclusion never records an answer, changes mastery or deletes past evidence. Existing receipt-recovery controls remain available; no backend, model routing or dependency changes.

## Verification

- Missing-control regression reproduced before implementation.
- 11 focused component tests pass, including editing/local Run while excluded, disabled submission/hints, failed refresh, retained code and hint exposure, and invalidated checks after restoration. Isolated browser-session storage in tests to avoid inherited pending receipts.
- Two isolated real sandbox browser journeys pass at390/1280: keyboard opening/restoration/refresh, real exclusion API, unchanged draft, Run availability, hint guard, focus recovery and no horizontal overflow. Screenshots visually inspected. No model inference or real learner data changed.
- Frontend lint, types and production build pass; existing bundle-size/jsdom canvas warnings remain.
- Bounded code/pedagogy review clear for the primary code assessment. Linked explain-back remains separate; no broader completion claimed.

## Remaining

Linked explain-back, challenge and listening need their own controls and answer-preserving recovery. A hidden control while a submission receipt needs reconciliation is intentional: resolve the earlier submission first. Concurrent changes from another tab still use existing server eligibility/version rejection and receipt recovery. Human comprehension and physical audio/screen-reader gates remain open.
