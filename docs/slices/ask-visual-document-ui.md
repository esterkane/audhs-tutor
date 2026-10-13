# Ask diagram document and version navigation

## Change
Saved diagrams now come from the answer-scoped document API rather than the latest
20 generation receipts. Request history remains for generation/status/stop/recovery.
Separate paginated document/version selectors expose manual diagrams, older documents,
the latest saved version on reopening and explicit historical versions. Archived
history is available through an explicit toggle; active presentation excludes it.
Origin labels use stored version origin, with unknown remaining unknown. No inference
on browsing and no changes to grading, competency, scheduling or source permissions.

Document/version selections stay pinned during refresh. Page changes reset selection
explicitly; a missing selected document is reported instead of silently selecting
another one. Nested disclosure events cannot change the outer panel's open state.
Review history stays readable for historical/archived versions. New review creation
is disabled there, but uncertain exact-key requests and retained notes remain available.
A code review caught the initial recovery-control omission; corrected before release.

## Verification
662 frontend tests, full lint/types and production build pass. Ten sandbox browser
journeys pass: 390/1280px layouts, 21-document pagination, latest/historical versions,
reopening without generation, archived history, exact-key recovery after archiving,
existing generation/review retries and renderer/read failure recovery. Screenshots
inspected at both widths and axe/no-overflow checks pass. Existing diagram journeys
also exercise reduced motion and enlarged text. Bounded review has no remaining
blockers or majors. Backend unchanged from 1557 tests.

Keyboard focus/Tab and existing keyboard button actions were checked. Headless native
select ArrowDown/End sequences did not reliably select the intended option; final
version-selection assertions use Playwright selectOption. A complete manual native
keyboard-select/screen-reader check remains open; do not claim full keyboard-only
acceptance. Tests also needed an exact diagram-heading selector to avoid matching the
answer heading. Existing ResizeObserver notification warnings and intentional renderer
failure logs remain; production build retains the existing large-chunk warning.

## Remaining
Archive/restore commands and structured version editing still need UI controls.
Archived views explicitly disclose that restore is not available here yet. These
navigation changes do not complete the accepted visual lifecycle or establish model
semantic correctness. Next implement reversible archive/restore with durable recovery,
then structured editing and explicit compare/recovery for stale document revisions.
