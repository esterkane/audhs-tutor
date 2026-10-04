# Audio-lab return context

2026-10-04. Reproduced: open the audio visualizer from Complete the transformation, then use Coding playground. The selected workspace incorrectly becomes Free experiment, hiding the learner's saved code.

The outgoing link now includes a workspace identity. The visualizer resolves only existing activities and names the return destination. Refresh retains that destination; unknown identities show an explicit message and a fixed local playground fallback. No arbitrary return URL, learning writes, new dependency or audio-state change is introduced.

Verification: original failing narrow browser reproduction; four original desktop/narrow workspace-history and audio-detour journeys passed after the fix. Three sanitized browser checks passed (desktop/narrow keyboard return, refresh, retained code, no API writes, unavailable origin). 26 focused unit tests, lint, TypeScript and production build passed. Narrow screenshot inspected: return destination wraps cleanly; no horizontal overflow. Existing canvas-test, worker and bundle-size warnings remain.

## Remaining C3 boundary

This restores the coding origin, not visualizer playback across route exits. The visualizer currently owns File/AudioInput, position and transient editor state inside its route and disposes on unmount. A subsequent slice must define an app-lifetime paused workspace with explicit Resume, source retention/reselection and audio-owner cleanup before moving that lifecycle. Do not keep audio playing invisibly or serialize private files into browser storage implicitly. Lesson-linked visualizer entry also needs a truthful relationship to the skill; a generic audio exercise is not evidence for every lesson. Full C3 and owner comprehension remain open.
