# Audio visualizer learning lab

Owner requested both tutor integration and a later standalone macOS visualizer based on deep-research-report(7).md, starting inside the tutor.
First slice: /playground/visualizer, explicit silent demo or user-selected local file → Web Audio features → validated JSON graph → Canvas rendering. Teaching explains each stage with hints and a bigger-picture view.
No database, mastery, session, event, API or provider change. The built-in guide uses no model; audio never leaves the tab. Files are not recorded or persisted. Presets may be saved/exported explicitly.
Low energy offers a short still-sample path. Existing sensory sound and reduced-motion settings apply. Stop and tab-hidden/unmount cleanup release audio resources. Controls use labels and keyboard-native elements.

## Acceptance
- Bounded typed nodes, DAG validation, finite ranges; invalid presets retain last working visual. No executable shader or script input.
- Explicit start/stop; race-safe cancellation of file startup. No autoplay, microphone or other-app capture.
- Local audio analysis reports RMS and normalized bands honestly; no beat/tempo claim.
- Three visual modes, graph display, editable/exportable JSON, guided predict/change/compare steps.
- Preset/audio engine tests, component/axe tests and isolated browser journey; code and pedagogy review.

## Scope and native continuation
The report recommends Swift/Core Audio/Metal for its standalone target. This browser teaching adaptation uses existing TypeScript/React and Web Audio/Canvas, with no dependency or native architecture replacement. Schema v1 is this lab’s bounded subset, not full compatibility with the report’s proposed passes/shaders format. A separate native implementation should share feature/preset semantics through an explicit versioned converter, then implement process capture and Metal. No Spotify API/private metadata API or hardware permissions introduced.

References checked: https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode and https://developer.mozilla.org/en-US/docs/Web/API/AudioContext/createMediaElementSource .

## Verification and review

377 backend tests (creative-selection change), 72 frontend tests, full lint/types pass. Focused visualizer tests cover graph cycles, absent references, duplicate IDs, range errors, non-string enum rejection, finite outputs, RMS/band boundaries, invalid edit retention, storage, axe, repeatable sampling, sound changes during deferred audio opening, natural completion and resource cleanup. Initial isolated browser journey passed with a generated silent WAV and no non-GET requests; final full journey result recorded in HANDOFF.

Required code review fixed stale sound permission during file startup, enum coercion and ended-file cleanup. Required pedagogy review fixed non-repeatable before/after experiments and guide instructions against arbitrary restored graphs; numeric output and node values added. Both re-reviews cleared blockers/majors. Native macOS capture/Metal, beat tracking, custom shaders and model-generated presets remain future stages, not claims of this slice.
