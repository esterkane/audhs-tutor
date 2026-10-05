# Saved-answer discussion streaming — 2026-10-05

## Problem
Saved-answer follow-ups still buffered the full model reply, although the ordinary study tutor streamed. A controlled component test delivered an early token while holding completion and reproduced the absence of visible text.

## Implementation and boundaries
The existing follow-up implementation now serves both buffered and SSE endpoints. Both use the same owned parent, request fingerprint, historical context, model routing, output limit, final disclosures and save-only recovery. The existing bounded SSE queue and shielded worker cleanup moved to a shared helper; no new inference policy or dependency was introduced.

AnswerFollowup reuses the existing stream parser. Preview text is explicitly unfinished, not checked or saved as an answer. Stop, interruption and navigation retain it in the current tab with storage-failure warnings. Earlier interrupted previews remain separate when retrying. Only the authoritative final response advances the saved parent. Replay uses the original parent/question/key and never feeds preview text back to the model. No learning-kernel, assessment or mastery writes changed.

## Verification
- Failing baseline: six original component tests passed, new early-preview scenario failed.
- 33 backend checks passed across answer history, playground and streaming; final four follow-up-specific checks passed after adding failed-save/partial-provider coverage. They assert ownership, immutable displayed-answer context, correction purpose, cross-transport replay, conflict, no duplicate inference, no assessment writes, save receipt and preserved lineage. Existing shared-transport tests cover real ASGI disconnect cleanup.
- Full backend suite:857 passed (three existing warnings).
- 47 focused frontend checks, then all 520 frontend tests passed. Ruff, mypy (199 files), frontend lint, TypeScript and production build passed; existing bundle-size warning remains.
- Four isolated browser journeys passed (1280px and390px saved-answer and study conversations). Keyboard send/preference actions, streaming-before-completion, final replacement, lineage and horizontal overflow checked. Both saved-answer screenshots inspected. These fixtures prove interaction, not model quality or physical audio.
- Independent code/pedagogy-boundary review found no actionable issue. No prompt, model selection or teaching policy changed.

## Actual local performance and remaining issues
A synthetic arithmetic follow-up ran through the real local gateway on a disposable database copy, with only Ollama available and hosted budget zero. Gemma3:12b delivered first text at13.053s and completed at14.915s. The reply correctly discussed the saved answer4 versus sum5. This single sample demonstrates earlier delivery than waiting for that completion; it does not establish a general speed or teaching-quality improvement. Prompt processing/first-text latency remains unresolved.

The final reply also carried the existing generic outdated-code-output notice although this arithmetic parent had no code/output. That misleading inherited disclosure needs a separate contextual fix and regression; it is not caused by streaming. The follow-up page remains long, and broader screen-reader/zoom/owner-comprehension coverage is open.

Next: inspect expensive prompt processing without dropping source/learner context or weakening quality; connect explicit assessment discussion only through the saved immutable parent. Full remote CI is tracked separately and must finish before treating all browser gates as passed.


Full remote browser run37319478975 (preceding70feac6) finished:228 passed,20 skipped,3 failed. Remaining: Home adaptation suggestion overflows at320px/200% text sizing (Choice stacking fixed the previously reproduced control overflow but not this separate populated card); visualizer coordination journey cannot locate the global Stop visualizer sound button; narrow visualizer canvas exceeds the expected500px top position. All other CI jobs passed. These are remaining release gates, not failures resolved by follow-up streaming.

Sanitized checkout verification:8 follow-up/shared-stream backend checks and TypeScript build passed. Publication guard runs against the staged sanitized delta.
