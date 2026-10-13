# Structured Ask diagram editor

The optional editor now exposes title, complete text, direction, concept labels and
explanations, relationship endpoints and meanings. Add/remove controls retain stable
part IDs and offer up to 20 in-mount undo steps. A validated local graph preview is
explicitly unsaved and unverified. No generated executable code or inference is used.

Starting checks the latest active version and freezes document revision, version ID
and hash. Drafts use the existing scoped tab/memory recovery; partial invalid fields
remain editable while save/preview are disabled. Source/binding data comes from the
immutable base, never editable metadata. Save creates a new version with the original
revision and a durable request key. Retry sends the submitted body, not later edits.
Successful saves retain the draft; late callbacks cannot erase it. Historical/archive
views retain draft and retry access but do not permit a fresh save.

Conflicts keep the draft and expose a read-only latest-version comparison. No silent
rebase or automatic merge occurs. The learner can open the latest version and start a
separate edit, manually carrying across selected changes. Recovery text is available
for copying before explicit discard. Undo history itself is not persisted on reload.
The existing tab-store size limit may require keeping a copy of large drafts; warnings
remain visible. Source-derived edits stay local and do not inherit presentation reviews.

Verification: 668 frontend tests, full lint/types/build pass. Fourteen sandbox browser
journeys pass; the two editor journeys rerun after undo support cover remove → invalid
save blocked → undo, reload retention, preview, lost response, later edits retained,
same-key replay, latest-version opening and conflict comparison. Keyboard save activation,
390/1280px layouts, axe scan and no-overflow checks pass; screenshots inspected. Bounded
code/provenance review found no blockers/majors. Backend unchanged from1557 tests.
No learning kernel, grading, source permission or paid-model behavior changes.

Remaining: manual native-select/screen-reader acceptance, larger graph usability,
semantic quality of generated diagrams, and the reviewed learning-exercise integration
in the lifecycle plan. This is structured manual editing, not automatic factual correction.
Existing ResizeObserver notifications and production chunk-size warning remain.
