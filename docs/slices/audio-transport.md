# Local audio pause, resume and seek

Continue the familiar single-controller player: Pause retains file/context and position; Resume continues; Stop disposes and later Play restarts. Keyboard-native playback timeline seeks only after playback has loaded metadata, enabled while playing or paused. Seeking resets smoothing and picture; file-driven oscillator time follows playback position.
No second player, upload, API, dependency, learner events or mastery change. Respect sound/reduced-motion and stop on hidden/unmount. Resume completion must not revive replaced/stopped audio. Position remains outside live announcements; explicit action status only.
Verify transport boundary/race and seek clamping, route pause/resume, and real browser seek then stop. Waveform remains overview-only; timeline owns seeking.

Verification: 87 frontend tests, isolated Chromium pause/seek/resume/capture/stop journey and make lint pass. Tests include clamped and nonfinite seeks, disposed resume rejection and Stop during pending Resume. Code and pedagogy reviews: no blocker/major; clarified Capture requires resumed playback after paused seeking. No new dependencies or backend behavior changes.
