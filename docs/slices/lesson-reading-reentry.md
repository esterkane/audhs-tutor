# Long explanation re-entry — 2026-10-05

## Original reproduced problem (S3; bounded fix below)

After a completed explanation, choose a later section, write a note, enter a question, return to explanation and reload. Before reload the section reader retains its position. After reload the text returns as a full Markdown document, but the section controls, editable note field and **Try a question** action disappear. Notes remain recoverable through Saved lesson notes. This raises re-entry cost and prevents the normal explanation-to-question continuation without another generation.

The browser scenario uses a prepared twelve-section SSE reply and the real sandbox session/checkpoint and assessment retrieval. No hosted model is called. The first test assumption (all sections visible together) was corrected to use the existing section reader. The next failure reproduced the missing reader after reload at both390 and1280px.

## Evidence and scope

`frontend/e2e/lesson-reading-journey.spec.ts` originally recorded the pre-fix behavior, including the limitation explicitly; a passing baseline is **not** a fix. It exercises keyboard question/return activation, retained explanation without regeneration, note recovery and horizontal overflow at390/1280. Screenshots cover the question and restored text. It does not exercise grading, repeated incorrect answers, human comprehension or audio output.

## Implementation contract

Inspect the tutor draft persistence contract and completed-turn identity restoration before editing. Session currently renders LessonReader and the question continuation only when `done` exists; restored text has no completed-turn metadata. Preserve original turn identity, exact text and source provenance for a genuinely completed reply, while keeping stopped/interrupted/unknown outcomes distinguishable. Do not manufacture completion metadata from the existence of text. Keep older text-only drafts recoverable. Likely files: tutor stream/draft persistence, Session.tsx, their tests and this browser journey. No mastery, scheduling, grading or routing change is required.

Acceptance: reload restores the same section, editable notes and question action for a completed reply, without another model call; incomplete replies remain honestly incomplete; unavailable/corrupt storage and older drafts remain readable. Replace the explicit absence assertions in the baseline with the desired restored controls after implementing. Review persistence/version compatibility before expanding scope.

Verification: two Chromium baseline journeys pass; focused ESLint and TypeScript build pass. Narrow question screenshot inspected: controls and answer choices remain readable, no horizontal overflow; first question still requires vertical scrolling. No runtime files changed, so production build was not repeated.

## Implemented recovery

The cache now stores optional completion-v1 metadata sharing the exact enclosing text. Only an `ok` reply with complete status, matching text, original turn identity and valid source/details structure is restored as a completed reply. No model request, grading or learning-state write is triggered. The existing reader key restores the chosen section and editable notes; Try a question uses the existing checkpoint transition. The restored-message copy identifies a browser-restored completed reply, not a fresh check.

Legacy text-only caches remain readable without manufactured metadata. Partial/stopped streams retain their existing recovery behavior. Invalid or unknown completion metadata leaves text available with a warning. Large replies are stored once; if metadata exceeds the existing250000-character bound, the latest bounded text is saved alone with an explicit warning. Storage denial retains the active UI and existing warning path. No server schema or library change.

Verification:39 focused unit tests;6 browser journeys (completed re-entry390/1280, partial retry desktop/narrow, existing visualizer recovery390/1280); full frontend lint, TypeScript and production build pass. Known worker_threads externalization and bundle-size warnings remain. Narrow restored-reader screenshot visually inspected: chosen section12, note and question action visible; no horizontal overflow. Keyboard activation enters the question both before and after reload. Independent code/learner-clarity review caught duplicated-text size growth; versioned shared-text encoding plus overflow fallback fixed it, and follow-up review is clear.

Remaining: older text-only drafts cannot regain unavailable completion metadata; oversized metadata falls back explicitly to text. This does not verify repeated wrong-answer feedback, model correctness, physical audio or owner comprehension. Next: continue the integrated question/incorrect-answer/help/return journey. This closes this bounded reload defect, not the full daily-learning acceptance stage.
