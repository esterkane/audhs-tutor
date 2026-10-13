# CSV replacement preview recovery — AU-IMPORT-03

## Problem and implementation
A failed replacement preview removed edited vocabulary rows and could replace their source label before the replacement succeeded. Reproduced with an HTTP503 at320/1280 before the fix; both regression scenarios failed at the retained-row assertion.

VocabImport now swaps reviewed rows, metadata and source only after the replacement returns usable rows. File-read/size/request failures and empty replacements retain existing nonempty reviewed rows. Invalid editable rows are still accepted for correction; row-count warnings remain visible. The UI identifies the reviewed source and explicitly states that Import uses the retained rows. Existing operation locking and explicit Start over remain intact.

Only frontend preview behavior changed. Vocabulary identity, deduplication, scheduling, grading and backend APIs are unchanged. No libraries or model calls added.

## Evidence
- Eight component tests passed: failed request, unreadable/oversized file, empty response, successful replacement, edited payload/source, explicit confirmation, removal undo, accessibility check and import failure.
- Five isolated Playwright scenarios passed: pending controls, double clicks, preview timeout/recovery and replacement failure; desktop1280/narrow320, keyboard confirmation, original source plus edited content in request, no document overflow.
- Desktop/narrow screenshots inspected. Narrow row table remains horizontally scrollable within its labeled keyboard-focusable region.
- Full lint/type checks and production build passed (existing bundle-size warning remains).
- Code and pedagogy reviews found no blockers/majors. Empty and successful replacement cases are component-tested; browser scenarios cover failed replacement.
- Logs: /tmp/csv-replacement-{unit,after,lint,build}.log. Screenshots: /tmp/csv-preview-replacement-{320,1280}.png.

## Remaining limits
Drafts are not persisted across unmount/reload. Explicit Start over still clears the preview. This slice does not introduce preview cancellation or claim screen-reader/human acceptance. Continue the wider reliability and learner-flow checklist separately.
