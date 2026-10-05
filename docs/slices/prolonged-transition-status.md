# Prolonged transition status

2026-10-05 — bounded daily-learning acceptance slice.

## Problem and implementation
Session and review transitions could remain pending without explaining the delay. After 15 seconds, a polite status now explains that the server may still be processing, offers the existing Pause/Home path, and states that there is no automatic retry. The notice timer follows the shared in-flight promise and is cleared on settlement/unmount. All four transition mutations explicitly disable retries. No request deadline, cancellation, server outcome or exactly-once guarantee is implied.

Practice Log/Skip controls now reflect pending block transitions; Pause remains independent. Existing tokens and native disabled controls are retained. No backend, grading, competency, FSRS, source-selection or routing changes.

## Evidence
- Before implementation, three delayed-response scenarios failed because no notice appeared after 16 seconds.
- Final original checkout: 28 unit tests across transition, practice, Session and Review suites; 11 session-pause browser journeys; frontend lint, TypeScript and production build passed.
- Unit tests cover the 15-second boundary, shared promise/double-call behavior, settlement and retry suppression despite global retry defaults.
- Browser routes commit a real sandbox transition then hold its response. Start, movement and review show the notice, permit Pause, ignore late navigation, and resume the actual checkpoint with one transition request. Movement verifies Log was enabled before transition and both Log/Skip are disabled while pending.
- Desktop and 390px journeys include keyboard Pause/re-entry. Final narrow screenshot inspected: readable notice, visible exit, disabled practice actions and no visible horizontal overflow. Synthetic delays test UI behavior, not model speed.
- Independent code/pedagogy-oriented review found no actionable issue, including the practice follow-up.
- Existing build warnings remain: optional worker_threads externalization and large bundle; unit canvas warning is inherited.

## Remaining
This does not bound server execution or establish cancellation/idempotency beyond existing contracts. General navigation races, repeated-error learning guidance, full zoom/assistive-technology checks, physical audio and owner comprehension remain open. Next inspect repeated wrong-answer and misunderstanding recovery without changing learning policy speculatively.

Sanitized checkout verification: same 28 unit and 11 browser tests passed, plus lint and TypeScript. Original production-build evidence reused for identical source delta.
