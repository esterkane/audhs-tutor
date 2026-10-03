# Read-aloud status (UX26-06, first slice)

Show preparation, queued playback, completion and explicit stop beside requested speech.
Make muted/zero-volume output visible without opening settings; preserve explicit sound choice.
Inputs are existing text, speech responses and shared audio settings; no model/API/event changes.
Use polite status text, retain keyboard Stop and existing volume/speed/device controls in every mode.
Pause/resume and cross-surface playback coordination remain subsequent UX26-06 work.

## Verification and review
- Regression reproduced before fix: missing preparation state (313 passing, one failing).
- Full frontend: 316 tests / 81 files; focused ReadAloud: six tests.
- Two isolated Chromium journeys passed: shared settings and 320px requested reading, keyboard stop,
  muted notice and completion using synthetic PCM. This does not prove physical headphone audibility.
- ESLint and production build passed; existing large-chunk and wavesurfer worker warnings remain.
- Code and pedagogy reviews: no blockers/majors. Added inter-passage/completion-release coverage;
  changed mute advice to “adjust playback” because browser state cannot prove device audibility.
- No backend/API, learner evidence, routing, dependency or sensory-default changes.

## Remaining
UX26-06 is partial: pause/resume, cross-surface coordination and real output-device checks remain.
Owner comprehension and manual assistive-technology gates remain open.
