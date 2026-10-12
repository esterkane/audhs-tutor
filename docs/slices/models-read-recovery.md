# Models registry read recovery

2026-10-12 — follows the Models observation in the adversarial usability audit.

Reproduced at320/1280px: a503 registry read leaves no error explanation or retry.
The list now distinguishes loading, unavailable, confirmed-empty and failed-refresh
states. The existing boundedRead helper limits transport waits to15s; automatic
query retries are disabled. Loaded registry data remains visible on refresh failure.
Explicit retry keeps its button mounted and focusable while preventing duplicate
reads. Success transfers focus to the registry only if the retry button still owns
focus; a learner who moves elsewhere keeps control.

Scope: Models.tsx and the useModels read hook. No mutation, routing assignment,
benchmark, download, learning policy, backend or dependency changes. Other Models
reads (routing/jobs/search/costs) retain their existing behavior and need separate
coverage; this is not complete settings recovery.

Verification: existing Models component test passes; ESLint, e2e TypeScript and
production build pass (existing chunk warning). Four isolated browser scenarios
cover initial503, held retry/duplicate Enter, both success-focus cases, confirmed
empty, cached503 and failed retry at320/1280. Narrow recovered screenshot inspected.
Code/learner-control review found unconditional success focus could steal focus;
fixed and covered by held-response tests, follow-up review clear.
Initial cached-state tests raced navigation commit; final tests wait for Models
unmount before Back. No production navigation change was made for that test race.
Human/AT and broader dark/zoom acceptance remain open.

Integration context: earlier sanitized run38242874022 completed all gates successfully.
Latest-head CI is separate and remains pending; do not use that old head as proof
for this slice. Both repositories remain private.
