# Clear tutor focus and follow-up conversation

Let the learner choose a notebook step for tutor help and show the current target explicitly.
Keep a readable conversation and a follow-up composer after the tutor response, including answer feedback.
Socratic questioning is explicit and reversible: one question, learner response, feedback; explain mode remains available.
Preserve separate drafts/conversations by target and guard stopped or stale requests. No mastery, grades, routing or progress changes.
Verify target isolation, follow-up history, Socratic reply guidance, storage failure, narrow screens and keyboard use with synthetic data.

## Reproduction

The exported UI shows only the latest tutor reply beneath its response box, no named focus, and no next-step guidance after a Socratic question. Answer-feedback mode has no follow-up composer.

## Verification

Implemented named notebook step focus, isolated target conversations, last-20-exchange visible history (last three exchanges sent to the tutor), response-before-composer layout and follow-up for answer feedback. Socratic mode is opt-in, labels the expected reply and supports Explain instead. No execution, assessment, mastery or provider changes.

- 22 focused StudyTutor/NotebookWorkspace tests; full frontend suite: 184 pass.
- `make lint` and `make test-backend`: pass, 421 backend tests.
- `pnpm build`: pass; existing large-chunk and spectrogram worker externalization warnings remain.
- Isolated Chromium `study-conversation.spec.ts`: desktop 1280px and narrow 390px pass, including keyboard start, step selection without editor movement, contextual follow-up, earlier messages, draft restoration and no page overflow. Existing answer-feedback journey also passed.
- Initial browser assertions used exact label text for native selects; Playwright includes option text in that lookup. Changed assertions to semantic combobox name; production accessible name was correct.
- Independent code and pedagogy review: no blockers/majors. Existing storage/stale-request tests remain green.

Limitations: synthetic model responses do not certify live tutoring quality. Manual VoiceOver and user comprehension are not certified. Visible history is bounded and older long messages can be shortened; current-work model context stays bounded. Tutor focus itself defaults to current cell when reopening the workspace, while per-target conversations restore when selected.
