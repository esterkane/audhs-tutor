# Explicit workspace teaching mode

The chosen direct-explanation or Socratic mode must travel as typed request state, not only embedded wording. Guided tutor actions send the effective selected mode; ordinary playground/help defaults to direct explanation. Historical candidates must match that choice. Responses should address supplied numbers/code rather than substitute a generic analogy. No evidence, score, autoplay or mastery change; existing explicit mode controls remain the accessible UI.

Implement a versioned workspace prompt and evaluate real local responses separately from request/state tests. Do not claim prompt compliance just because a flag is transmitted. Existing saved replies remain readable; incompatible old prompt/mode records must not be exact-replayed.

## Implemented contracts

`PlaygroundRequest.questioning_style` defaults to explicit and accepts only explicit/socratic. StudyTutor sends the same effective action state it displays (including Socratic replies/hints and Explain instead); generic playground defaults explicit. The selected mode sits outside quoted workspace/history. Historical candidates require the same mode; missing legacy modes miss. Workspace prompt version v6 prevents incompatible exact replay. Existing history remains readable. No model routes or paid dependencies changed.

The versioned task prompt requests literal current-work reasoning, direct explanations without gratuitous quiz questions, opt-in Socratic feedback and bounded hints. These are instructions, not enforced correctness guarantees.

## Evidence and remaining quality failures

477 backend tests, frontend suite, lint/types and production build pass. Two isolated Chromium journeys (1280/390px) verify selected request modes, follow-up, Explain instead, retained drafts and keyboard controls. Twelve focused backend tests pass after the final prompt wording. Code/pedagogy review found no blockers in the typed-state implementation; model-quality acceptance remains separate and OPEN.

Six synthetic explicit-mode trials (`prompt-v6.json`) corrected wrong prior arithmetic and did not obey injected completion instructions; none appended a question. They still omitted supplied percentages in the comparison case, emitted representation/citation-like labels and sometimes overstated fairness. That sample used the first draft of v2 before the extra formative-attribution sentence.

Three initial and three revised Socratic samples are preserved in `workspace-modes-v6.json` and `workspace-modes-v6-final.json`, with task-prompt hashes. The model incorrectly attributes its corrected30/50=0.6 calculation to a learner who wrote0.9, even after an explicit instruction against that error. The final hint adds a question despite the hint-only request; a start question also phrases the ratio ambiguously. Do not describe these outputs as accurate formative checking. No quality gate passes from these diagnostics, and no general improvement is proven.

Next: evaluate feedback against the exact learner claim with objective arithmetic/attribution checks and compare already-installed local candidates before any routing decision. Request-state integrity is implemented; reliable model feedback is not solved.
