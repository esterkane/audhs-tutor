# Saved challenges without retrieval initialization

Opening an eligible, unattempted saved challenge now resolves its existing content before initializing retrieval. Excluded questions also return their existing unavailable response first. Only a generation miss initializes the repository; generation still performs the shared eligibility check. Ownership and node resolution precede reuse, and the displayed prompt and content token use one snapshot.

The API no longer eagerly injects Repo for this route. A small orchestrator reusable helper shares the previous cache/exclusion logic with generation. No provider, grading, scheduling, mastery or caching-eligibility policy change; previously attempted questions are not made reusable by this slice. No dependency/schema/UI changes.

## Evidence

- Before: two of three endpoint regressions failed when repository construction reported no installed embedder (saved and excluded questions). After: all21 focused endpoint/generation/selection/ownership tests pass, including retrieval failure for a genuine generation miss and no retrieval construction for saved/excluded questions.
- Removed the challenge browser start fixture. Two real sandbox desktop/narrow journeys now pass through the actual start/exclusion/restore/refresh endpoints without ready models. Synthetic saved question data remains isolated to the sandbox. Keyboard, focus, retained drafts/reload and overflow checks pass; screenshots inspected.
- Ruff, strict mypy207 and affected browser-file lint pass. Reused prior passing frontend build/component evidence because application UI code did not change. Bounded code/pedagogy review clear.
- Live backend restarted after checking owned process, no connected requests and no running imports; health checked. No live challenge was generated or answered.

This supersedes the offline-start limitation in challenge-question-controls.md. Linked code explain-back/listening controls and broader correction/replacement remain open. Newly generated challenges still require the configured retrieval/model services; this is not a fallback to unsupported content or an automatic hosted-model switch.
