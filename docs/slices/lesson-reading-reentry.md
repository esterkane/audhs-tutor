# Long explanation re-entry — 2026-10-05

## Reproduced problem (open, S3)

After a completed explanation, choose a later section, write a note, enter a question, return to explanation and reload. Before reload the section reader retains its position. After reload the text returns as a full Markdown document, but the section controls, editable note field and **Try a question** action disappear. Notes remain recoverable through Saved lesson notes. This raises re-entry cost and prevents the normal explanation-to-question continuation without another generation.

The browser scenario uses a prepared twelve-section SSE reply and the real sandbox session/checkpoint and assessment retrieval. No hosted model is called. The first test assumption (all sections visible together) was corrected to use the existing section reader. The next failure reproduced the missing reader after reload at both390 and1280px.

## Evidence and scope

`frontend/e2e/lesson-reading-journey.spec.ts` records the current behavior, including the limitation explicitly; a passing baseline is **not** a fix. It exercises keyboard question/return activation, retained explanation without regeneration, note recovery and horizontal overflow at390/1280. Screenshots cover the question and restored text. It does not exercise grading, repeated incorrect answers, human comprehension or audio output.

## Next bounded implementation

Inspect the tutor draft persistence contract and completed-turn identity restoration before editing. Session currently renders LessonReader and the question continuation only when `done` exists; restored text has no completed-turn metadata. Preserve original turn identity, exact text and source provenance for a genuinely completed reply, while keeping stopped/interrupted/unknown outcomes distinguishable. Do not manufacture completion metadata from the existence of text. Keep older text-only drafts recoverable. Likely files: tutor stream/draft persistence, Session.tsx, their tests and this browser journey. No mastery, scheduling, grading or routing change is required.

Acceptance: reload restores the same section, editable notes and question action for a completed reply, without another model call; incomplete replies remain honestly incomplete; unavailable/corrupt storage and older drafts remain readable. Replace the explicit absence assertions in the baseline with the desired restored controls after implementing. Review persistence/version compatibility before expanding scope.

Verification: two Chromium baseline journeys pass; focused ESLint and TypeScript build pass. Narrow question screenshot inspected: controls and answer choices remain readable, no horizontal overflow; first question still requires vertical scrolling. No runtime files changed, so production build was not repeated.
