# Project-study reflow — 2026-10-03

## Evidence

Linux CI failed the existing project-orientation journey at 320px viewport / 200% root text size.
Its screenshot and trace were inspected. The same journey on local macOS Chromium passed using
both native system font and Arial, so Linux equivalence is not claimed.

A reproducible wider-text stress case adds 0.12em letter spacing after the original 200% check.
Before the fix, document scrollWidth was 347px for a 320px viewport. Project-study grid children
measured 314.640625px wide, starting at x=32 and ending at x=346.640625, despite the available
256px content width. Failure output records actual element names, classes and rectangles.

The implicit project grid column retained a content minimum. Defining one explicit
`minmax(0, 1fr)` column (`grid-cols-1`) lets it fit available width. This one-class fix passes the
same geometry assertion; no clipping, reduced font size, hidden controls or widened viewport.
A trial nested-card change was unnecessary and removed.

## Verification

- Project-orientation browser journeys: 2 passed, desktop 1280px and narrow 320px. Both retain
  navigation, notebook return, preserved notes, focus, no automatic lab start, axe checks, and the
  original 200% text assertion, then add letter-spacing stress. Disposable sandbox ports8041/5205.
- Changed-file ESLint and TypeScript build check passed.
- Independent code and pedagogy reviews clear; two integration browser journeys passed.
- Linux CI rerun remains pending. The local stress reproduction proves
  the layout defect, not that the Linux failure has been conclusively resolved.
- No learner data, API, dependencies or model routing changed.
