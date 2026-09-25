# V2 bounded block authoring

Create the five existing block types with validated safe defaults and unique bounded IDs; remove only unused blocks, with actionable dependency errors. All pointer and keyboard operations use the same draft/validator. Draft undo/redo stores at most 50 valid checkpoints; incomplete JSON never reaches playback.
Explicit file import validates current browser JSON with a 16,000-byte limit, then previews name/count before replacing the draft. Reset discloses replacement with applied settings. Apply, Save and Export remain separate. No new dependencies, API, schema, events, model calls or mastery changes. Existing sensory/energy behavior remains.
Acceptance: add/connect/edit/undo/apply/save/reload; reference deletion refusal; invalid import, cycles, unknown versions and prototype-like IDs; audio transport intact. Checks and review complete; see below.

## Verification and review

At the combined V1–V3 checkpoint: 100 frontend tests, 3 isolated Chromium journeys, make lint and production build pass. Browser tests cover desktop/narrow disclosure preservation, keyboard Apply/Save, block creation/reconnection/edit/undo/save/reload, dependency-safe removal, explicit valid/invalid import/reset, existing real synthetic-file transport and unchanged paused position during experiments. No live learner database or model calls. Existing large-bundle and WaveSurfer capability-probe warnings are nonfatal.
Code and pedagogy reviews: no blocker/major; minor copy fixes included.
