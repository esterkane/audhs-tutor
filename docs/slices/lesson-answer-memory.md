# Historical context in lesson explanations

Learners can see which earlier answers informed a new lesson explanation and open them separately from corpus sources. Lookup is local, optional on failure, and does not replay answers or award learning evidence. Mode/energy and the current teaching contract remain authoritative; historical content has its own bounded, escaped context section. Links are keyboard reachable; no audio or motion starts automatically.

## Scope and safeguards

Literal search requires the same owner, skill, resolved action, questioning style and effective teaching-contract hash (including prompt version, hint level, representation/scaffold and spoken constraints). Older unkeyed records miss. Hidden/incorrect/outdated and memory-derived answers are excluded before the candidate limit. Up to five candidates are checked; at most two excerpts of 600 characters enter the independent 512-token history budget. Every saved source must still exist with the same text hash, with no newer local version. This establishes source currency, not answer correctness.

History IDs stay out of model-visible text and are retained in saved metadata and the completion payload. The UI explicitly labels history as unverified evidence. SQL lookup failures roll back their savepoint and preserve generation. Language conversation practice skips this lookup. No migration, new provider, paid call, exact replay or semantic lesson lookup is added.

## Verification

- Backend: 468 tests pass, including owner/scope/source/feedback/recursion exclusions, changed contracts, bounded escaping, completion provenance and database-error fallback.
- Frontend: 225 tests pass; new component test checks history disclosure/link.
- Lint/types and production build pass. Existing bundle-size and spectrogram worker advisory remain.
- Isolated Chromium explanation-reader journey passes with history disclosure and keyboard-focusable link.
- Independent code/pedagogy review fixed a major: matching action alone could import a later hint into an earlier hint request. Exact effective-contract identity now prevents it; re-review clear.

## Local model diagnostic, not acceptance of teaching quality

`uv run --project backend python scripts/eval_answer_memory.py --surface lesson --out evals/results/answer-memory/lesson-v1.json` ran six synthetic prompt-only trials against local Gemma, in a disposable database with hosted credentials disabled. The three paired cases cover correct arithmetic, wrong prior arithmetic and injected instructions. The model corrected 30/50 to 0.6 and did not obey the injected completion/fairness claim. No saved-answer IDs appeared as citations.

Quality gaps remain: the baseline bucket analogy incorrectly says the larger group loses more water; some history-conditioned replies add a question despite a direct-explanation request, and the injected-history reply exceeds the requested four sentences. This small sample does not prove accuracy, style adherence, learning benefit or a speed improvement. It does not exercise full retrieval latency or all production contracts. Broader quality evaluation and semantic integration for lessons remain open. Existing workspace semantic retrieval and opt-in exact replay are separate features.
