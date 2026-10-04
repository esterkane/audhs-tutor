# Linked coding tutor references and reuse

2026-10-04. C3 integration; broader workspace plan remains open.

## Problem addressed

The linked coding tutor previously had only a client exercise/goal and general help. Source-free prompt/disclosure and reuse could not simply be combined with retrieval. This change connects the existing bounded snapshot to explicit linked tutor requests.

## Implementation

The server validates lesson origin, resolves title/goal and searches local material with existing skill → course → corpus widening. Source passages retain their actual labels, not an assertion that every hit belongs to the current lesson. A separately versioned grounded prompt quotes the server contract and passages as untrusted data. Typed reply status distinguishes supplied, empty, unavailable and not requested. Reference panels are attached to individual replies and saved with browser chat, so numbered references stay with the answer after reload.

Saved answers include exact evidence text/hashes, identity and retrieval trace. Fresh exact reuse requires the same evidence/goal/contract plus existing corpus freshness checks. Completed idempotent retries return their original reply, including passages, without retrieving again. Missing embedding initialization and ordinary retrieval availability failures have bounded waits and disclosed general-help fallback. Cancellation remains cancellation. Standalone/program help, arithmetic/bin checking, routing, assessment and mastery are unchanged.

Citation checking accepts only in-range single numeric markers outside code; ambiguous/composite markers get a warning without destroying prose. A valid marker does not prove that the passage supports the claim. Reference panels say this explicitly. No code is automatically inserted or executed, and opening the page does not trigger retrieval.

## Evidence

- 55 affected backend tests passed in each checkout, covering new source supply, exact reuse, changed source, completed old replay, retrieval outage and repository-init fallback alongside prior recovery/memory/provenance behavior.
- Playground unit tests:9 passed. Frontend lint/types/production build passed; Ruff and targeted mypy passed.
- Disposable browser journeys:2 in each checkout,390/1280, keyboard disclosure and return link, saved code/question, source recovery after reload, no horizontal overflow. Browser tutor reply is a fixture; backend integration tests use actual endpoint/retrieval with synthetic corpus and fake model.
- Narrow result visually inspected. Fixed contradictory generic no-source copy after reload. Existing build warnings remain.
- Independent code review: two majors fixed (per-answer source persistence and repository initialization fallback); recheck clear. Pedagogy review found no blocking contract issues.

## Remaining work

No claim of real-model grounding quality: run a local sample with conflicting/irrelevant passages, empty retrieval, wrong learner answer and stale output; score claim support separately from marker validity. Test full human comprehension and long real source layouts. Reference panels expose supplied passages, not a semantic citation verifier or a full document browser. Source freshness is checked for saved reuse; concurrent index/corpus replacement is not locked across inference. Historical generated replies remain unverified context. Explicit starter-code suggestion/insertion and broader C4/C5 work remain next.
