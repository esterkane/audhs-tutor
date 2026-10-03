# Shared reading controls (UX26-06)

Expose current requested-reading status and Pause/Resume/Stop inside each shared Audio controls panel.
Controls operate the existing player, not another synthesis request. No auto playback or model changes.
Only the current lease can publish control state; release removes stale controls on stop/unmount/finish.
Keep inline controls available; identify this transport as reading, not all app sound.
Verify shared controls, pending transitions, ownership and keyboard/narrow journeys.

## Verification
Full frontend324 / 83 files, focused reading tests13, two isolated browser audio journeys passed.
The narrow browser journey operates Pause/Resume/Stop from the header controls with keyboard Resume/Stop;
component test verifies two panels control the same player without a new synthesis request.
Lease regression rejects stale control updates/releases. ESLint/build passed (existing warnings remain).
Code and pedagogy review found no majors/blockers. Physical audibility and owner comprehension remain open.
Other media and voice conversation are not yet coordinated by this reading-only transport.
