# Distinguish criterion from recorded evidence

Problem reproduced during the repeated-incorrect sandbox journey: a wrong answer
appeared as “selects the correct option — 9” beneath What to reconsider. The correct
answer was5 and grading was correct, but the joined phrase could read as endorsing9.
The shared AssessmentEvidence component now labels the criterion and recorded
evidence separately. Existing heading groups, exact text, feedback, scores and
learning state remain unchanged. No events, backend, inference or mode changes.

Use “Recorded evidence,” not “Your answer”: this field can contain grader comments
rather than a verbatim learner quote. Existing font/spacing tokens are used, with no
new interaction, library or motion. Empty evidence stays absent.

Validation:4unit tests,4real browser journeys (assessment feedback and three incorrect
attempts,390/1280) pass; ESLint, e2e types and production build pass. Browser keyboard
help/revision/pause/resume, saved-answer identity, unchanged review date, exactly3
observed submission POSTs and no horizontal overflow remain checked. Narrow rendered
feedback inspected before/after; labels wrap clearly. Build retains its pre-existing
large-chunk warning. Human comprehension/screen-reader acceptance remain open.

Code/pedagogy review found no blockers; added the suggested assertion preserving
criterion text. No automated check establishes that an unfamiliar learner understands
all feedback; this is a bounded wording/presentation correction.
