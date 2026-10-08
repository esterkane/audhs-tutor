# Draft editor reload recovery — R4

Story: a learner can reload and recover unfinished JSON edits without overwriting a newer server draft.
A versioned tab-local envelope holds draft ID, saved baseline/version, edited text and timestamp; the server remains authoritative. No API mutations, model calls, learning events or automatic merge occur on restoration.
No timed purge: explicit discard or acknowledged save clears that draft recovery; browser tab lifetime bounds retention. Storage errors preserve current page text and report limits. Unreadable records are not silently replaced; an explicit control may use current text.
Keyboard-accessible recovered-edit entry, visible storage status and unchanged sensory preferences.
Acceptance: reload/remount, changed saved revision, isolation, partial invalid JSON, failed storage, explicit discard/save cleanup, no automatic writes, desktop/narrow keyboard flow.
Baseline failing remount test: /tmp/draft-reload-before.log.

## Implementation and boundaries

A versioned sessionStorage envelope preserves partial JSON and its original saved revision. Recovery never saves or activates automatically; a changed server revision blocks saving until explicit reconciliation. The recovered-edit button opens and focuses the editor. Explicit discard or acknowledged save clears only that draft. Unreadable storage is preserved until explicit replacement; failed writes/removal warn without losing current page text. Closing a tab may lose recovery. This is not durable cross-device storage or automatic merging.

Learning selection, assessment and activation policy are unchanged. No backend changes or live curriculum mutations were required. Broader R4, human comprehension, browser zoom and screen-reader acceptance remain open.
## Verification — 2026-10-08

- Baseline remount regression failed before implementation.
- Full frontend suite: 550 tests / 110 files passed before final React lifecycle/focus compatibility adjustments; final affected hook/editor suite: 18 passed.
- Final four isolated Chromium journeys passed: reload and stale-conflict flows at 390/1280 widths, keyboard recovery focus, exact partial text, explicit discard, no automatic writes and no horizontal overflow. Both final screenshots visually inspected.
- ESLint, TypeScript and production build passed; existing bundle-size warning remains.
- Bounded code/copy review found no blockers or major findings; lifecycle adjustments also reviewed.
- Backend unchanged; reuse preceding 937-test pass rather than repeat. No hosted inference or real learner-data mutations.

Logs remain in /tmp/draft-reload-{full-ui,ui,browser,lint,build}.log; screenshots in /tmp/draft-reload-{390,1280}.png. CI at the new commit has not yet been verified.
