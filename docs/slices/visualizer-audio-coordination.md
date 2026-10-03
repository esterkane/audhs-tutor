# Visualizer monitoring joins shared audio controls

## Scope and acceptance

Continue UX26-06 audio ownership for explicit Visualizer file/test-signal monitoring. Silent analysis, synthetic demo and motion do not claim audio ownership. An explicit sound checkbox during playback or audible Play/Resume claims the same in-page lease used by readings. A replacement clears the sound checkbox and silences monitoring while keeping the input position, analysis and motion. Shared Stop sound only silences monitoring.

Enabling sound while paused only arms the checkbox; the existing reading keeps ownership until explicit Resume. Pause/backgrounding releases ownership; foregrounding does not resume playback. Returning from a test signal restores the prior source paused and silent. Preferences cannot automatically enable monitoring. Pending start/resume completion must not restore sound after replacement, or restore running UI after a background pause. Unmount disposes pending inputs and releases its lease.

No audio analysis algorithms, model requests, microphone access, backend or learning state change. Coordination is in-page, not across tabs. Browser tests use synthetic media and do not certify physical audibility.

## Implementation

Visualizer holds an identity-safe shared lease only for explicit monitoring. Replacement uses the existing gain muting path, leaves analysis running and announces why sound stopped. Pending file completion reads the current effective monitoring flag. Playback generations fence resume/start UI updates across pause, visibility and disposal. Shared controls expose stop-only Visualizer sound through the common owner contract.

## Evidence

Focused component tests cover silent non-displacement, explicit displacement, shared Stop preserving analysis and position, replacement during pending start/resume, silent test-signal return, backgrounding during pending resume, and disposal during pending start. The three core ownership regressions were reproduced against the pre-change component before applying the implementation.

Browser integration evidence is recorded with the integration changes; physical speaker quality and cross-tab coordination remain outside this slice.

Integrated verification (2026-10-03):17 focused Visualizer tests, full frontend356 tests across84 files,
production build/types and targeted ESLint passed. A browser composition journey using the real
Visualizer and ReadAloud components with silent Web Audio doubles passed: silent test signals do not
displace reading, enabling monitoring does, a new reading mutes monitoring, and shared Stop preserves
running analysis. That journey caught the notice previously hidden inside Create; notices now render
above the persistent canvas in all views. Independent code and pedagogy reviews clear. These checks
make no physical-output, microphone, model-quality or cross-tab claims.
