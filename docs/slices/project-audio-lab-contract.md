# Authored project-to-audio-lab connection

2026-10-04, C3. Current code inspection: project sections have task-notebook links but no typed audio-lab relation. AudioLessons exposes six stable IDs; the lab has only standalone coding-workspace returns. Do not invent topical relevance using keyword matching.

Add optional section.audioLab with a known lesson ID and a nonempty bounded purpose statement supplied by the material author. Old manifests remain compatible. Build fixed local URLs from encoded course/section IDs; never accept an arbitrary return URL. On arrival resolve the relation against the local manifest and show the named project step and purpose. An explicit Open linked lesson action changes only the selected Learn explanation; it does not start a signal, audio, motion, code or evidence. Keep existing lab drafts/settings intact and the existing explicit source-change controls. Missing/changed relation or manifest failure shows recovery without pretending the intended source is loaded.

Expected files: program manifest parser, guided section entry, focused lab context component, Visualizer integration and browser/component tests. No learning kernel, model/provider, backend API or database changes. Verify no writes/autoplay, specific lesson selection, named keyboard return, retained project notes, reload, missing relation, fetch retry/cancellation and responsive presentation. This contract does not yet constitute a completed integration or mapping of private course material.

## Implementation and verification

Optional section field example: `"audioLab": {"lesson": "frequency", "purpose": "Compare cycle spacing while keeping amplitude constant."}`. Allowed IDs: amplitude, frequency, harmonics, sampling, mapping, create. Purpose must be nonblank and at most600 characters. Nothing is inferred or added to existing private material by this slice.

The local link carries project_course, project_step and project_lesson. The lab revalidates that exact relation from the local manifest; missing/changed mapping does not silently substitute. Loading has a15-second deadline, cancellation guard and retry. The named project link replaces the unrelated coding return in this context. Existing standalone coding returns remain unchanged. Opening the linked explanation preserves existing visual and signal settings; start-signal controls remain separate.

16 focused component/parser tests pass, plus7 Chromium journeys: desktop/narrow project round trips, reload, known lesson selection, missing/changed mappings and existing coding returns. Browser checks observe zero AudioContext constructions and zero API writes on the linked flow; project notes remain intact. Keyboard entry/return and390/1280 screenshots inspected. Lint/types/build pass with existing worker/bundle warnings. Code and pedagogy reviews found no blockers/majors. Tests use synthetic content; no claim of educational relevance or live-course deployment.

Remaining: inspect actual local material before authoring any relation. Source/version identity beyond current relation validation, broader review-context tools, persistent tutor C5 and owner comprehension remain open. Full C3/design-plan completion is not claimed.
