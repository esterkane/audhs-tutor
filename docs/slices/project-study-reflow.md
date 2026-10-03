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
- The original fix passed independent reviews and integration checks; Linux revealed the nested defect below. The local stress reproduction proves
  the layout defect, not that the Linux failure has been conclusively resolved.
- No learner data, API, dependencies or model routing changed.

## Follow-up: inner lesson card (same day)

Linux rerun now passed original 200% check but failed the added spacing stress: document330px,
GuidedSection child column265.40625px from x65 to330.40625. The Understand control itself retained
that width. This is a second, nested intrinsic minimum, not the original outer project column.
The closed bookmark select also measured352px, motivating explicit fit before opening it.

GuidedSection now has an explicit zero-minimum column; phase buttons can wrap within available
width and grow vertically, with overflow-wrap:anywhere for the single long label. Card prose can
wrap unusually long tokens. Bookmark selection fits its container. No overflow is hidden.

The journey additionally checks phase-button scroll dimensions (no clipped text), opens bookmark
controls and rechecks reflow. Desktop and320px journeys2 passed with original200% and spacing;
GuidedSection componenttests5, changed-filelint and TypeScriptpassed. Linux follow-up remains pending.

Follow-up independent code and pedagogy reviews found no blockers or majors.
