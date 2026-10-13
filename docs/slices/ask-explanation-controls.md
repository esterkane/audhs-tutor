# Ask explanation controls

Saved Ask answers had a free-form follow-up composer but no direct depth/method
controls. Add an optional disclosure with Simpler, More detail and Show the method.
Each fills an editable question and focuses it; no automatic submission/inference.
Existing nonempty drafts and pending requests disable shortcuts rather than being
overwritten. Reuse existing draft persistence, branch linkage and request recovery.
No grading, learning scheduling, source rights, model routing or backend change.
A worked method is an explanation/derivation, not purported hidden model reasoning.

## Visual dependency found

G4 requires authored visual persistence/acceptance and answer-version provenance.
Current visual-learning-binding schema/read validators and prototype renderers do not
provide that lifecycle. Do not attach unsaved diagrams or arbitrary executable output.
Complete that bounded lifecycle before connecting Ask visual generation. This change
finishes existing G2 controls; it does not claim G4 implementation.

## Review fixes and verification

Visual inspection caught duplicated answer paragraphs during draft edits: the prior
citation slice gave SourcedAnswer and sibling AnswerChecks the same React key.
SourcedAnswer now has a distinct sources: key. A browser paragraph-count regression
failed before this fix and passes afterwards. Isolated component rerender also passes,
but did not reproduce the sibling collision and is not the principal evidence.

Final 15 Ask browser journeys pass at390/1280px, including keyboard shortcut/focus,
no implicit model request, reload/draft protection, explicit submit/parent linkage,
and one-copy answer rendering. Both screenshots inspected after repair. Full frontend
658 tests passed before the key repair, plus the two targeted SourcedAnswer checks.
Full lint/type checks passed; final route/test lint/type and production build passed
(existing bundle warning). Code/pedagogy re-review cleared the fix. Backend unchanged.
No hosted calls or live learner writes; private DB snapshot unchanged. Human/AT
acceptance and G4 saved visual lifecycle remain open; hosted CI billing block remains.
