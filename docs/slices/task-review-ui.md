# Optional task/rubric review screen

Problem: the review API has no learner-facing preview/confirmation; correction
editing should not be required merely to review an existing task. Baseline existing
question-report browser flow: 2 tests passed against disposable sandbox, 7.9 seconds.

Added a separate /task-review screen linked from collapsed Question practice options.
Reference content stays hidden until explicit reveal; objective, task and rubric are
rendered as text, never executed. Approval requires an unchecked confirmation and
explicit explanation/application choice. Review is described separately from grades,
understanding and independent work. Revocation preserves history. Uncertain saves
reuse the exact command, rapid duplicate requests are guarded, and task changes reset
component state. Learning logic and model routing are unchanged. Existing tokens used.

Verification: 646 frontend tests passed across 127 files; focused8 include explicit
reveal/confirmation, exact-command uncertain retry, duplicate guard, revoke facet,
stale409 fresh confirmation and unmount cancellation. Lint and production type/build
passed. Three isolated browser tests cover 320/1280px, keyboard confirmation, focus,
no horizontal overflow, return link and held-save focus-away. Desktop and narrow
screenshots inspected. Existing chunk warning remains. Browser API responses are
synthetic; real owner/transaction semantics are covered by the prior21 backend tests.

Review fixes: removed nested main landmark, preserved originating path in return
link, retained reveal button focus while loading, and prevented slow saves stealing
focus after navigation to another control. Bounded code/pedagogy review has no
remaining blockers/majors. Applied previously disposable-tested migrations to local
DB (d257a941be03 and 4ab714cf670c), then refreshed private snapshot.

Remaining: human/assistive-technology acceptance; approval does not yet qualify
performance. Next freeze receipt-or-none in prepared grading requests before
inference, preserving older request replay and never backfilling attainment claims.


2026-10-12 zoom acceptance: two isolated Chromium cases pass at actual 200% tab
zoom (light 320 CSS px; dark 640 CSS px). Keyboard reveal, explicit confirmation,
close/reopen reset and no review writes verified; no horizontal overflow. Native
compositor screenshots inspected: readable wrapping and visible focus controls.
E2E TypeScript and targeted ESLint pass. Bounded code/pedagogy review found no
blockers or majors. This test-only delta changes no learning logic. Human and
assistive-technology acceptance remain open. Subsequent binding and Progress
qualification are already delivered; see progress-reviewed-labels.md.
