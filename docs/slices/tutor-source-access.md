# Tutor source access

Q2: assessment hints/explanations gain the same inspectable source passages as lesson explanations. Reuse the guarded SourceViewer and existing report API; bind open passage/report to the completed turn and chunk, reset on new turn, restore citation-button focus on Close. Preserve cited/uncited, flagged and withheld distinctions. No source means no source, not verified general knowledge.

Show StudyTutor source limitations alongside its reply rather than only inside technical details. SourceViewer distinguishes missing passages (404) from temporary/network failures and allows explicit retry. Citation presence is not proof of factual support. No new backend/retrieval/model routing or learning evidence.

## Verification and review

- Lint/types and production build pass (existing bundle-size and spectrogram worker warnings remain).
- 199 frontend tests pass, including exact passage opening, focus restoration, turn selection reset, no-source labels and 503-to-success retry. Existing 404/report tests retained; fixture uses generic source and guarded app link.
- Isolated Chromium assessment journey passes with a synthetic streamed hint, keyboard-opened citation, visible passage and Close focus return. No live learner database or model call used.
- Independent code/pedagogy review found no blockers or majors. Failed refetch hides cached text so a removed/unavailable passage is not presented as successfully loaded.
- No prompt, backend, dependency or routing changes; tests prove UI behavior, not factual support or model accuracy. Manual screen-reader evaluation and broader Q2 quality remain open.
