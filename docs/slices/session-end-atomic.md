# Atomic session-end recap — AU-RECAP-02

## Finding and boundary
Failure injection reproduced an ended session whose recap write could fail independently. The previous implementation committed the session before writing its ENDED event, and retry returned early. This could lose the notes/self-report permanently.

The kernel end function now owns one short transaction: conditional UPDATE of an open session, refresh current ORM state, append its matching ENDED event without an intermediate commit, commit both. Failure rolls back both. Competing database sessions preserve the first successful end and its optional recap, without overwriting it on replay. No schema or learning policy changed.

This is deliberately NOT a claim that the entire HTTP end operation is atomic. Recall scheduling, running-block closure and checkpoint pruning occur before this boundary in separate helpers. A broader transaction design remains to be specified. Historical partial records are not silently rewritten.

## Verification
- Before-fix injected event failure left ended_at committed; regression failed as expected.
-54 backend tests pass (new failure-after-event-flush, commit-failure rollback, concurrent workers, replay; existing kernel/session transitions/clarity/experiments/adaptation suites).
- Four real-sandbox browser cases pass: recap draft reload/save and delayed End navigation at390/1280. Optional notes retained, fields locked during save, saved confirmation and draft cleanup verified. Keyboard editing/navigation, no document overflow and screenshots inspected.
- Full lint (Ruff/format/mypy283 app sources, frontend TypeScript/ESLint) passes. Frontend code unchanged; prior production build remains applicable.
- Code and pedagogy reviews: no blockers/majors. No model calls, new dependencies or migration.
- Evidence logs: /tmp/recap-atomic-{before,after,lint,browser}.log. Screenshots /tmp/recap-draft-{390,1280}.png.

## Next
Reconcile competing recap Save/End/Change-topic controls and unknown save responses before closing the recap recovery flow. Human audio/assistive-technology acceptance and broader R3/R4 remain open.
