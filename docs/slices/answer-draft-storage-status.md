# Answer draft storage warning — R4

2026-10-13. Reproduced in an isolated browser: sessionStorage quota failure left the selected answer in memory without warning that refresh would lose it. Baseline journey failed specifically at the missing alert assertion.

The existing draft helper now exposes per-key failed-write status. Session shows an adjacent alert that the answer is available in the open page but must be copied before reload/close. A later successful write clears the warning. Clearing a graded draft clears the warning and retains existing error-tolerant cleanup. No grading, scheduling, model, server data or curriculum change.

Verification:12 focused draft/Session tests; two sandbox browser journeys at390/1280px with keyboard selection, enabled submission control and no horizontal overflow. Screenshots inspected at both widths. Targeted ESLint, full frontend type checking and production build pass (existing large-chunk warning). Code review reports no blockers/majors. Browser journey uses a real disposable session and simulated browser-storage failure; it selects an MCQ without submitting evidence. It does not prove refresh persistence, screen-reader announcement quality or full R4 coverage.

Remaining: draft envelopes are still tab-local; denied storage cannot survive reload. This warning covers original Session answers, not a redesign of all draft surfaces. Revision recovery retains its existing independent handling. Content-version and learner-scoping improvements remain separate R4 work; no automatic purge introduced.
