# Clear lesson activation

The learner can distinguish searchable material, editable lesson drafts and active lessons without understanding curriculum schemas.
Choose one course, review existing section drafts first, then explicitly activate the selected section. Creating new drafts and source-role settings are secondary.
Preview goals, practice, assessments and linked evidence in readable form. Keep JSON editing collapsed and prevent activation of unsaved edits.
Use existing endpoints and events; no automatic publication or learner-data changes. No mode/energy switch; keyboard controls, labelled status/errors and reduced visual density in every mode.

## Acceptance
- Passed: course-scoped existing drafts first; readable goals, examples, practice, questions and grading criteria; advanced JSON and source settings collapsed.
- Passed: explicit activation success/failure, validation blockers, unsaved edit/discard safety, draft switching, refreshed version conflicts, source-role changes and course loading failures (8 component tests).
- Passed: question-specific evidence opens within its lesson; missing sources and non-array grading data are labelled explicitly. SourceViewer reused without changing provenance or file access rules.
- Passed: axe accessibility check; real browser inspection of course selection, section review, exact source passage and layout. Section heading receives focus. Browser inspection was read-only: no live activation or edits.
- Final checks: `UV_NO_SYNC=1 make lint` and `UV_NO_SYNC=1 make test`: 333 backend and 51 frontend tests passed.

## Review fixes
Code and pedagogy reviews found stale version precedence, detached source display and absent question-specific sources. Fixed and regression-tested; pristine editors follow newer versions, dirty edits show a conflict and block overwrite. Both re-reviews report no remaining blockers/majors; test cleanup minor fixed.

## Limits
Detailed editing remains an advanced JSON workflow. Dictionary grading data is labelled for advanced inspection rather than guessed. Existing server APIs remain unchanged; this is not a multi-user concurrency guarantee. Activation still requires the learner's explicit action.
