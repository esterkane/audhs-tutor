# C2a area location — 2026-10-04

Baseline reproduced at390/1280: selecting an area did not update the URL; refresh lost it. Areas now writes area/draft query parameters and follows same-route history. Other query parameters remain. Browsing emits no learning writes and leaves goal/session policy unchanged.

Unsaved lesson-draft or area-setting edits retain the currently mounted editor when history changes the URL. A notice offers Keep editing here (restores URL) or saving before following the requested location. This does not protect full-page reload or leaving the Areas route; no durable-editor claim. Area edits track a saved baseline and synchronize canonical save results without replacing newer typing. Independent review caught normalization locking; corrected with a delayed-save regression.

Five unit tests pass: existing draft eligibility/deep links, unsaved draft/history and canonical-save/newer-input retention. Three browser tests pass:390/1280 history/refresh/keyboard keep-editing with no API writes, plus existing rename/goal workflow. Whole lint/types/build pass with existing build warnings. Narrow screenshot visually inspected (../ux/evidence/area-location). Before fix two baseline tests failed as expected. No new dependency or backend/learning calculation change.

Only part of C2: global area selector/recent contexts, unknown/empty/error recovery and broad dirty-route protection remain. Current Areas still mixes browsing and curation; no claim of finished learner-facing area workspace. Uploaded design reference is reconciled separately before further visual changes.
