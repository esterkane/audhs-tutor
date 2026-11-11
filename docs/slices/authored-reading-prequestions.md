# Authored questions before accepted passages

The knowledge editor accepts an optional before-reading question for the explanation and
a separate optional question for the worked example. These are authored explicitly in Review,
alongside the lesson fields. They are not the application/assessment question. Saving or
activating a question does not verify its factual quality.

## Accepted snapshot and identity

The existing authoring JSON stores the two optional strings; no migration is needed.
Published drafts are immutable through the draft API. Revising one creates a new draft ID,
so edits to an unpublished revision cannot change the accepted reading question.

The accepted-reading endpoint reads only the published snapshot and emits a question when
its stored passage exactly matches the current accepted LearningObject passage. It includes
the passage SHA-256 and a question ID derived from target, exact passage and exact question.
Question-only activation can reuse the same LearningObject version; the reader also includes
the published draft ID, so a newly accepted question cannot reuse an earlier prediction.
Mismatched, blank or unavailable legacy associations are omitted without guessing.

Create-request fingerprints omit only empty new optional fields to preserve idempotent replay
of requests made before these fields existed. Nonempty questions remain part of the fingerprint.
Old browser forms normalize omitted fields to empty defaults without marking unchanged work dirty.

## Reading and recovery

Questions appear at the start of their authored passage in section view. The existing Markdown
parser keeps headings inside code fences out of navigation; source fields supply exact passage
offsets instead of matching ambiguous heading labels. Nested headings remain ordinary reading
navigation. Documents requiring cross-section Markdown definitions retain full-document rendering.

The learner can predict, skip, or select Full explanation at any time. Full reading does not erase
a previous prediction. After reveal, the exact authored question, original prediction and separate
reflection/correction remain visible. The immediate attempt is saved in the browser with its prompt. The learner can explicitly save the prediction to their profile for later recall.
Reading notes and bookmarks use their existing independent storage.

A restored bookmark bypasses a new question only for its originally restored section; it does not
silently skip an unseen later passage question. Missing/invalid storage leaves reading available.
An older question or accepted version keeps its original record; no records are migrated by guessing.
Saved-answer lessons without authored prequestions retain their existing generic prediction path.

An enrolled prediction is tied to the accepted draft, question and learning-object version. After 24 hours the Review screen offers a fresh response before showing the original prediction and passage. The stored passage remains available for comparison after revisions. Longitudinal learning outcomes still require observation. This activity uses no model calls, grades, competency evidence or FSRS writes.

## Verification

- 13 authoring backend tests passed, including publication/revision/activation, exact passage
  binding, distinct target identities, unchanged assessment question, legacy request replay,
  conflict on changed content and zero model/assessment/competency/memory writes.
- 46 focused frontend tests passed across prediction, reader, authoring and recovery components.
  New regressions cover full-reading escape, independent passage attempts, retained notes,
  question identity changes and resume followed by an unseen question.
- Ruff format/check, targeted strict mypy (three source files), TypeScript build and changed-file
  ESLint passed. Full browser integration is a separate final gate.

## Integrated acceptance

The full frontend suite passed 878 tests across 168 files. Combined authoring/hybrid/oracle-manifest
backend checks passed 52 tests with 3 explicit opt-in skips; the independent real PostgreSQL run
separately passed all 26 oracle checks. Existing dependency warning remains unchanged.

Two new Chromium journeys passed at 390px and 1280px (17.8 seconds total), using actual UI authoring
fields, save/reload, activation, an unpublished question-only revision, passage prediction/skip,
notes, reload and the original prediction. Accepted reading remains identical after unpublished
revision. No tutor generation occurs. Axe and horizontal-overflow checks pass; both rendered
layouts were inspected. The full focused upload/research/write/review/activation/reading/feedback/
resume journey also passed (19.5 seconds total).

Early new browser fixtures were corrected to use the actual Review field location, stable
accessible textbox names and the existing publication/revision API shapes. Those failed fixture
runs are not acceptance evidence. Independent review found and fixed the genuine unseen-section
resume bypass; its focused regression passes. No history or assessment policy is changed.

The existing generic reading/feedback/recap journeys also passed at both widths on the final code (17.7 seconds total).
