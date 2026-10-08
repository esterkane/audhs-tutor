# Listening question practice controls

Listening questions reuse explicit exclusion/restore controls. Exclusion keeps the question, answer and player mounted, disables checking/validation, and does not stop local playback or record mastery. Reporting a wrong question remains a separate action. A restored question requires an explicit bounded refresh of the same assessment before checking; unmount cancels that refresh. Unavailable task errors link to exclusion management.

Freeform answers use the existing tab draft helper. Multiple-choice re-entry restores the choice label for reference, never a numeric selection that might now mean something else. Changed question/options similarly clear the selection while preserving the prior label. An empty selection never means option zero. Successful grading clears the submitted draft only when no newer answer has been typed; completed feedback recovery already requires exact answer/id/version matching. Storage denial has the helper's page-memory fallback, not guaranteed reload durability.

## Evidence

- Two missing-control regressions failed before implementation. Final 13 focused tests pass: cloze/MCQ re-entry, exclusion, failed refresh, unchanged clip position, reordered options/explicit reselection, fresh-token submission and newer text during grading.
- Three isolated browser journeys pass: existing audio ownership/pause/resume regression, plus 390/1280 keyboard exclusion/restore/refresh with focus and no overflow. Lesson/task/media are synthetic fixtures; question-state mutations and refreshed content use real sandbox APIs. No model or physical sound was used. Screenshots inspected.
- Frontend lint, types and production build checked; existing bundle-size/jsdom media warnings remain.
- Bounded code/pedagogy review found empty-selection attribution to the first option; corrected in both refresh paths and covered by remount/reordered-options tests.

No backend, schema, routing, grading rubric or scheduling changes. Physical audio/Bluetooth and human comprehension remain separate acceptance gates. Linked code explain-back controls and the reviewed correction/replacement workflow remain open.

Final review reassessment found no remaining blockers; completed-feedback recovery already guards the current answer before clearing its draft.
