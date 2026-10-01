# Readable, chunked project learning

User need: enough context to answer, deeper questions and a clear learning path. Replace the stacked project-study form with a responsive outline and a focused Understand → Try → Think deeper sequence. Worked examples and authored challenges are optional manifest data, never inferred factual content. Keep sources, hints, audio, tutor and pause reachable; preserve per-question work. Navigation position is not mastery. Shared Markdown typography improves reading throughout the app.

Requirements: desktop/narrow outline and reading layout; direct phase and adjacent-step navigation; sufficient explanation plus concrete examples; deeper questions with hints/criteria; saved independent answers; stopping audio when hidden; existing public/private separation. Evidence and remaining scope to be updated after checks.

## Implemented and inspected
- Persistent desktop outline; compact mobile selector; clear selected step and previous/next navigation. Guided lesson and notebook are separate views.
- Understand → Try → Think deeper, with optional authored examples/challenges, hints and criteria; no answer required to navigate. Old saved notes/answers/bookmarks are preserved; challenge answers are independent.
- Markdown typography shared across explanations, notebook text and tutor answers: bounded measure, stronger headings, list spacing, readable code/tables and theme-aware surfaces.
- Private guide enriched with six illustrative worked examples and twelve reasoning/transfer questions. Examples are explicitly authored illustrations, not dataset results. Source-specific research remains private.
- DOM and screenshots inspected on desktop and 390px width. No horizontal overflow at narrow width; viewport restored. No quiz submitted on the source service.
- Review fixes: phase-aware tutor context includes the worked example; phase change unmounts previous helper/audio; practice notes reach the tutor rather than an unrelated answer.

## Follow-through
Generated-session reading and deeper reasoning scaffolds are implemented in `session-reading.md`. Disposable browser journeys cover keyboard navigation and light-theme 200% text at 390px as well as desktop dark theme; project navigation now wraps under large text. Owner comprehension and retention effects remain unmeasured; automated checks are not a platform-wide accessibility certification.
