# Read-aloud pause and resume (UX26-06)

Learners can pause requested speech and resume at the same position without re-synthesis.
Suspend the existing audio context; arriving passages stay queued and must not resume it.
Stop remains available during pending audio operations; stale completions cannot update a replacement.
Keep explicit audio opt-in, shared volume/rate and all learning modes unchanged; no API/events change.
Verify preparation pause, queued arrivals, resume, stop/unmount races and browser keyboard use.
Cross-surface coordination and physical output-device checks remain separate.

## Verification
Full frontend319 / 82 files, focused9, two isolated Chromium audio journeys passed.
Browser checks include 320px layout, pause during synthesis, keyboard Resume, finish and Stop;
synthetic PCM verifies browser lifecycle, not physical audibility. Player test checks queued start
times are retained while suspended; component test checks late pause completion after Stop.
ESLint and production build passed (existing chunk/worker warnings remain).
Code and pedagogy reviewers found no blockers/majors. No backend or learning-state change.
Cross-surface coordination, own-device listening and owner comprehension remain open.
