# Verified course paths and reading estimates — 2026-10-25

## Delivered

- A shared, read-only LearningBreadcrumbs primitive displays actual content context with a
  named navigation landmark, ordered list and current-step semantics. Long names wrap.
- Guided project lessons show manifest course title → section title → saved Understand/Try/
  Think deeper phase. Task notebook, full notebook and paused views retain their actual context.
  No course IDs are substituted for titles and no browsing preference changes a session topic.
- Ordinary sessions show active subject → active skill → persisted activity phase. SessionOut
  has no course identifier; inventing a course from today's browsing/goal preferences would be
  misleading. Missing/stale active skill data remains explicitly unavailable.
- Accepted material shows its title/version → current reading section. Saved explanations show
  saved lesson/version → section. Reading notes/bookmark keys, full text, source metadata,
  histories, activation, grading and completion rules are unchanged.
- A restored guided phase is explicit. Revisiting an existing course/section route restores its
  own notes/phase; this does not introduce a new per-course step-selection store or erase work.
- ReadingTime shows a rough estimate for the currently visible text, recalculated on section,
  full-reading or guided-phase changes. A disclosed engineering assumption of 200 words/minute,
  rounded up to whole minutes, is not an empirically measured learner pace or remaining time.
  Code fences, indented code, inline code, block formulas, URLs and reference definitions are
  excluded; prose-only headings are not counted. Code-only/empty or unsegmented CJK content has
  no numeric estimate. Working through examples, notes, listening and practice can take longer.
- The estimate is memoized per text. Link parsing is bounded rather than backtracking over
  arbitrary long bracket sequences. No new request, model call, countdown, dependency, tracking,
  database schema or stored-data migration. No changes to hosted authoring or ordinary routing.

## Incoming GitHub findings

Completed d0bd787 CI: backend, frontend, migrations and Claude bridge passed. Browser job had
480 passes and 6 failures:2 legacy-motion cases (already fixed in 289afb0), plus 4 typography cases
that manually set the old data-font size attribute. The typography tests now target data-text-size
while retaining the original 118%actual-size assertions. Latest 289afb0 CI has passed backend, frontend, migration and bridge checks; the browser job was still running when checked;
its remaining typography failures are addressed in this slice, not represented as a green run.
Public CI logs were inspected; no private archive or learner data was used for diagnosis.

## Verification

- Full Vitest: 787 passed. Full ESLint and TypeScript passed; affected files rechecked after final
  fixes. Production build passed, with the pre-existing large entry-bundle warning.
- 13 browser cases passed: new course paths/reload/focus/notes at 390/1280; project orientation,
  missing links, browser-history and notebook return at 320/1280; checked source research in
  German/English; full lesson reading/question/revisit; lesson focus and explanation reader.
- 7 more existing cases passed: four typography theme/width cases and three full session-plan/
  review/stop-resume journeys. New authored-material lifecycle: 2 passed at 390/1280 with real
  sandbox HTTP/storage for save/activation/session/assessment/recap and 0 generation calls.
- The new lifecycle checks title/version/section breadcrumbs, reading estimate, exact reading
  note and section restoration after Pause/Home/Continue, understanding-check path, deterministic
  feedback, revisit and saved recap. The source-research cases independently cover Research →
  Write → Review with actual local checked calculations. They are not a model-quality benchmark.
- New browser path/lifecycle tests run axe on main; course paths reflow at 200% text and preserve
  keyboard access/focus mode. Unit tests cover counting boundaries, German/CJK, code-only input,
  topic isolation and active-session provenance. Existing source/progress assertions remain.
- No backend code changed. Reuse prior 2,339 passed / 1 skipped backend regression rather than rerun
  unchanged tests. All browser writes were confined to the disposable seeded sandbox database.

## Limits

The estimate is deliberately coarse, not a speed or accessibility guarantee. Complex Markdown,
tables, formulas and individual reading needs vary. No Firefox/Safari or human screen-reader
result is claimed. Optional graphics effects remain uninstalled. These changes do not resolve
remaining model factual-quality or notebook checklist items. See the private handoff for release,
CI and installation state; do not publish local handoff history or acquired course manifests.
