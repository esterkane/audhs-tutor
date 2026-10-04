# Server-validated lesson origin

2026-10-04. C3 partial implementation; source-grounded tutoring remains open.

## Problem and change

A linked coding request could pass its browser preflight and still be accepted after the selected lesson changed. A failing API test reproduced a model call for that stale origin. The request now carries an optional typed skill identity, validated against the learner-owned live session, unexpired checkpoint and existing skill before a new durable claim or model work. Rechecks follow asynchronous answer lookup. Navigation identity is excluded from model evidence. No learning-kernel writes, routing changes, dependencies or automatic execution were added.

Legacy requests omit the new field when serialized, preserving previous fingerprints. An identical completed idempotent request returns its original response even after the lesson changes; a fresh stale request is rejected with a return-to-lesson explanation. The browser retains its existing code/chat recovery behavior.

## Verification

- Backend origin, playground and workspace-recovery suites: 26 passed in each checkout. Includes stale origin/no claim/no model, valid completion and replay, changed origin during lookup, legacy serialization and prompt exclusion.
- Original frontend Playground suite: 9 passed; lint/type check and production build passed. Generated API types refreshed with make gen-api.
- Isolated lesson-playground browser journeys: 2 passed in each checkout at390/1280, including typed payload, saved work, return/reload, keyboard link and ended-origin behavior. Narrow screenshot inspected: readable stacked controls and visible return path; no layout change in this slice.
- Ruff and targeted mypy passed. Independent code review found no blockers or majors.

## Remaining limits and next step

This does not retrieve lesson sources or establish source-aware answer reuse. The UI still labels responses as general guidance with no retrieved sources. Next implement the bounded evidence/retry contract in lesson-playground-evidence-plan.md before changing that label.

The asynchronous-change test mutates through the same database session; separate-connection races are not proven. No lock is held across inference, so this does not guarantee atomic consistency against every concurrent lesson change. A request rejected after its durable claim can remain unresolved under existing uncertainty semantics; automatic retry is not introduced. Physical audio and owner comprehension are not tested by these journeys.
