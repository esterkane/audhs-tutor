# Work-alongside panel recovery

2026-10-04, bounded C3 slice. Browser reproduction: open Work alongside, visit the lesson coding experiment, return; the chosen panel disappeared. The failing390px journey reached the return and could not find Working alongside. An earlier locator ambiguity was corrected before this reproduction.

AlongsideMode now remembers the panel visibility in tab-scoped sessionStorage with version/session identity. Only the matching session restores it; closing is remembered. Storage denial/malformed data leaves the panel usable with a clear warning. The record contains no lesson text, audio, elapsed time or progress. Together still owns audio cleanup and its timer; reopening does not start sound and resets that panel timer, explicitly disclosed. No learning state, preference, adaptation, mastery or API changes.

Verification:7 focused component tests (including existing Together behavior), lint/types/build,2 desktop/narrow Chromium round trips including keyboard Space/Enter, reload, preserved question/code and Undo. Screenshots of the restored panel at390/1280 were inspected with no horizontal overflow. Code and pedagogy reviews found no blockers/majors; minor timer wording clarified. Existing build warnings remain. This is not VoiceOver/Bluetooth or owner comprehension evidence.

C3 remains partial: project/review contextual entry and a truthful lesson-to-audio-lab relationship need contracts before adding links. A generic audio lab must not imply relevance or completion for every lesson. Persistent cross-route tutor remains C5. Standalone Together remains accessible at its old URL; this slice preserves the embedded choice, not a globally running companion or timer.
