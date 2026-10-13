# Exact-version presentation review in Ask

A learner can record Presentation reviewed or Needs correction with an optional
note on the displayed saved diagram. The record binds the exact immutable version,
content hash and source snapshot; it is not factual certification or learning evidence.
No model call, assessment, competency, FSRS, adaptation or course publication follows.

## Before and implementation

The displayed draft exposed grounding and text but no way to record the learner's
judgment. Added optional review controls below its text/source section, using existing
versioned command and historical-review APIs. Server checks the current document
revision and latest version. Grounding problems disable positive review, retaining
correction reporting. Existing backend source/trust checks remain authoritative.

Notes use scoped tab draft recovery. Mutations freeze exact identity/decision/note
before sending. An uncertain response exposes explicit same-key retry; no automatic
resubmission or silent new revision. Later note edits are not cleared by a reply.
Saved history is labelled a dated presentation judgment of this version only.
Review recovery wording describes saved reviews, not model calls. No new dependencies.

## Scope remaining

Editing/replacing and archive/restore UI remain pending. Model factual/semantic
accuracy is still unqualified; this is learner feedback, not independent validation.
Latest-version conflicts keep the note and report the server conflict; this panel
currently displays the generation's exact saved version, not a full version editor.
Human comprehension and assistive-technology acceptance remain separate open gates.

## Verification
662 frontend tests pass; full lint/type checks and production build pass. Final
seven sandbox browser journeys pass, including keyboard review actions, 390/1280px
layouts, accessibility scan, reload, lost-response same-key retry, later-note retention,
both review decisions, history and revision conflicts. Review screenshots inspected:
controls wrap at narrow width and notes/status remain readable. Diagram renderer was
still lazy-loading in these review screenshots; existing diagram journeys cover rendering.
Targeted types/lint repeated after the sibling-key correction. Bounded code/pedagogy
review found no blockers or majors. Backend unchanged from 1554 passing tests.

Existing ResizeObserver notification warnings remain in diagram journeys; the intentional
renderer-failure test logs its caught import failure. No duplicate-key warnings remain.
Native zoom and screen-reader acceptance were not newly tested in this slice.
