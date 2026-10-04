# C5 companion context foundation

Implemented the first boundary in persistent-tutor-contract.md before changing presentation.

- Shell no longer recreates the companion on pathname changes. Original page title/path and applied material remain visible; the return link uses a validated local path.
- Editing a material draft does not remount the conversation. Apply uses a new opaque capture identity; the immediately previous capture can be restored. Existing StudyTutor continues to isolate conversations by session plus identity and preserve exact pending request recovery.
- Active, draft and one previous capture are versioned in tab storage, with 12,000-character text bounds and validated restoration. Storage failures retain in-memory work; malformed checkpoints are disclosed rather than silently overwritten before explicit capture.
- Reopen uses the retained capture, not silently the current page. Closing unmounts the existing request/media components and restores launcher focus. No sound or inference starts from opening, navigation or restoration. StudyTutor remains a whole-response request path, not token streaming.

## Verification

A pre-change disposable journey reproduced disappearing unsent questions on material edits and lost companion state after navigation/Back, plus duplicate sibling-key warnings. Replaced that baseline probe with recovery assertions.

33 existing StudyTutor/shell component tests pass. Five companion browser journeys cover desktop/narrow edit/apply/previous context, route/Back, reload with unapplied edits, close/reopen focus, blocked storage, invalid external return paths, 200% text reflow, and an interrupted request whose explicit retry reuses its original body/key. Four Library regression journeys pass alongside these. Final equivalent checks run in the sanitized variant. Lint, types and production build pass; known spectrogram worker/bundle warnings remain. Desktop/narrow screenshots inspected. Independent code/state and pedagogy reviews found no blockers/majors; launcher and capture-limit wording clarified.

These journeys use a fixture current session and a synthetic reply. They do not certify physical microphone/Bluetooth behavior or cancellation of server work. Existing media unmount cleanup is retained, not replaced. No backend, learning logic, model routing or dependencies changed.

## Next bounded work

C5 presentation remains outstanding: desktop side panel and narrow-screen sheet, top-level entry, focus trap/return and resize behavior without duplicate tutor instances. Current below-page placement is intentionally still the old layout, not acceptance of the final authoritative design. One previous capture is not the C7 recent-context history. Cross-session owner expectations and human comprehension remain open. Do not claim all streaming surfaces are unified by this whole-response companion change.
