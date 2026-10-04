# Area-scoped skill map

## Problem and implementation

The whole skill graph previously appeared regardless of the area being browsed. The map now has explicit URL-based scope (`/map?area=ID`), an All areas choice, and an explicit link from the selected browse area. Scope changes do not change the current session or goal.

The read-only map endpoint validates the area and projects stored `SkillNode.area_id` membership plus its transitive prerequisite closure. Related edges do not expand membership. Visible edges and Mermaid use the same projection; an accessible prerequisite list names the relationships. Outside-area prerequisites are labeled separately. Mastery, memory, unlock rules and next selection are unchanged; copy distinguishes current learning settings from the map filter. No schema migration, model call or new library.

Queries and mounted map content are keyed by scope. Mermaid instances have distinct IDs across scope mounts. Empty/unknown areas never fall back to unrelated skills. Catalog failures retain global recovery. Whole-map links and selected-lesson eligibility flow remain available.

## Verification

- Nine backend tests (area scope plus existing Stage 2 kernel/API): exact membership, transitive prerequisites, unrelated exclusion, unchanged state, empty/unknown scope and whole-map regression.
- Existing Map component test passes.
- Six browser journeys across 390/1280 widths: map recovery, scope changes, refresh/Back/Forward, empty/invalid areas, catalog failure, late response, diagram/list relationships, no learning writes, no page overflow at 200% text, keyboard focus and Enter on learning/retry controls.
- Scoped desktop/narrow screenshots inspected with the Mermaid rendering present.
- Frontend lint/types/production build, focused backend Ruff/mypy pass. Existing spectrogram worker_threads and bundle-size warnings remain.
- Equivalent focused backend/browser checks run in the sanitized checkout; API types regenerated there independently.
- Independent code/state and pedagogy reviews found no blockers/majors; incorporated more precise next-selection and unavailable-area wording.

Native select ArrowDown/Enter simulation did not reliably commit a selection in this headless Chromium environment. Browser coverage uses selectOption for scope choice and verifies native focus plus keyboard links/retry. This does not certify native popup keyboard operation in every browser, VoiceOver or owner comprehension.

## Remaining scope

C4 Library organization/source discovery remains next; C4 as a whole is not closed. Large-map readability/performance and owner comprehension remain open. Stored membership is authoritative for filtering but its curricular quality is not established by these tests. No area assignments or learning evidence were created by this slice.
