# Repeatable local audio sections

Offer optional explicit repeat range after playback metadata is available. Enable jumps to start; paused playback remains paused. Native timeupdate wraps approximately; natural file end can wrap too. Pause retains range; Stop/new file/demo clears it. Manual seek explicitly turns repeat off. Half-second minimum and finite duration bounds validated both UI and audio boundary.
No new library/API/events/mastery or hosted calls. Range not persisted; sound and motion preferences retained. Label approximate boundaries, no sample-accurate editing promise. Accessible numeric controls, status only for explicit enable/disable, no announcements per wrap.
Test validation, wrap/disable/pause/cleanup and real browser range controls. Reset smoothing at wrap for repeatable visual state; waveform remains overview only.

Verification: 88 frontend tests, isolated Chromium real-loop wrap/controls/stop journey and make lint passed. Review fixed major stale repeat-play rejection on Pause with operation generation; dedicated regression and focused tests pass, final frontend lint/types pass. Code re-review and pedagogy review clear blockers/majors. Browser loop boundaries intentionally approximate.
