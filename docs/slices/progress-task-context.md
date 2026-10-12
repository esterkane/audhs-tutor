# Progress task and help context

2026-10-12 — bounded read-only disclosure after the provenance foundation.

Progress previously could not expose stored task/help facts. Its evidence endpoint
now projects complete version-1 snapshots only when fingerprint, grading route,
hint report and revision parent match the owned attempt. Cross-skill attempt
references are hidden. Missing, malformed, future-version or conflicting snapshots
return null; historical task edits do not rewrite the saved task facts.

The existing evidence history has a keyboard-operated Task and help context
Disclosure. It distinguishes original/revised work and rubric version, discloses
partial help observations and unknown external help/solution exposure, and never
certifies independence or attainment. Existing dates, counts, result labels,
pagination and saved-assessment links remain. No model calls, migrations, learning
writes, grading, scheduling or new dependencies.

Verification: 12 backend tests (Progress + provenance), Ruff, configured strict
mypy (229 source files), frontend ESLint, e2e TypeScript and production build pass.
Four isolated Chromium journeys pass (9.7s), covering320/1280px, keyboard disclosure,
unknown fallback, pagination retry, duplicate retry suppression, saved-answer
navigation/Back and no POSTs. Narrow open-state screenshot inspected; reflows
without horizontal overflow. Bounded code and pedagogy review found no actionable
issues. Production build retains the existing chunk-size warning.

Limits: browser records are synthetic fixtures; backend tests exercise genuine
saved grades. Human comprehension, assistive technology, dark/zoom coverage for
this new disclosure and stronger assistance observations remain unverified.
These are historical facts, not rubric eligibility or attainment labels. Next:
versioned eligible task/rubric metadata before activating the owner-approved
task-specific passed/attempted labels. No score-to-label shortcut.
