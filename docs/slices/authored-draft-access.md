# Course-independent draft access

The lesson-draft page fetched authored/area drafts but hid them unless a course was selected.
Show null-course drafts by title in the initial list and reuse the existing review editor.
Keep explicit activation, dirty-draft navigation guards and existing course sections intact.
No learning logic, API, dependencies or design tokens change. Keyboard review focuses the
existing editor heading; narrow layouts use the existing responsive list and controls.

The previous live browser inspection reproduced the hidden draft. Now four sandbox journeys
pass at 1280/390 widths: read failure/retry, keyboard opening and editor focus, return/reload,
zero writes, axe and overflow checks, plus existing dirty-draft/server-conflict recovery.
Both screenshots inspected. 668 frontend tests, lint/types and production build pass.
Required bounded review found no blockers/majors. No backend change; reuse 1559 backend pass.
Existing large-chunk build warning remains. Manual screen-reader and owner comprehension are
unverified; the course selector still precedes the cross-topic list. No activation occurred.
