# Ask citation navigation

Saved Ask citation markers were plain text; learners had to open a disclosure and
manually match passages. Known markers now open the historical passage and focus
its heading. Back to answer citation restores the originating control's focus.
Unknown markers, code and existing links are not converted. The reusable Markdown
renderer only activates this behavior with explicit source keys and a callback;
other callers retain ordinary Markdown. No source text/learning logic/model calls change.
Existing snapshot and not-fact-checked warnings remain; navigation is not validation.
Use shared colors/focus styles, native buttons/disclosure and existing page layout.

## Verification and limits

658 frontend tests, 13 Ask browser journeys, full lint/mypy/TypeScript and production
build pass (existing bundle warning). Browser tests exercise keyboard citation entry,
exact heading focus and return focus at390/1280px; screenshots visually inspected.
Unit checks preserve code/link markers and unknown IDs. Code/pedagogy review found
no blockers/majors. No backend change; previous backend result retained.
Only saved Ask answers gain this navigation. It does not determine whether a claim
is supported or source is current; snapshot/status warnings and separate review remain.
Human/assistive-technology acceptance remains open. GitHub CI on preceding head
c9d1465 never started: payment/spending-limit annotation, not a failing code test.
Local validation does not substitute for latest-head hosted CI acceptance.
