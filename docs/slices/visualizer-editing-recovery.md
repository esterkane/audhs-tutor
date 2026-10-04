# Visualizer editing recovery

2026-10-04. First implementation slice from visualizer-route-recovery-plan.md; media/lesson recovery remains open.

A bounded versioned checkpoint stores raw editor text, validated applied graph, up to 50 valid undo/redo snapshots, active view, renderer and named graph identity. Raw unfinished JSON is preserved independently from the graph. Existing Undo semantics remain: undoing invalid JSON restores the previous valid checkpoint; that invalid text is not a redo entry. Named collection Save remains explicit and separate.

A resource-free app-lifetime memory checkpoint retains edits on route changes even when browser writes fail. Browser storage supports reload recovery. Invalid or unsupported stored data is not overwritten; current work remains in memory with honest warning and Export editing draft. Recovery does not start audio or animation, create sessions or write mastery. Unit isolation resets the tab checkpoint before each test.

Evidence: 59 visualizer unit tests, lint/types/production build pass. Original desktop/narrow journeys verify invalid text across route return and reload, keyboard Undo and no horizontal overflow; narrow screenshot visually inspected. Six sanitized browser checks pass, including storage-denied route return/export plus prior coding return regressions. An initial browser test used the wrong Undo accessible name; corrected to Undo draft before verification. Existing canvas-test and worker/chunk warnings remain.

Remaining: file/position, lesson controls, imported-but-not-applied file preview and MilkDrop preset selection are not recovered. Browser storage is shared between tabs (last persisted write wins); there is no cross-tab conflict merge. Full C3, integrated media lifecycle and owner comprehension remain open. Next implement paused-media descriptors and explicit Resume following the plan, including stale async disposal and previous-file restoration after tone lessons.

Independent read-only code/pedagogy review found no blockers or majors; checked graph/draft separation, corrupt-storage preservation, memory fallback, honest recovery wording and no restored playback flags. Reviewer did not rerun tests.
