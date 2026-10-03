# Home topic readiness — 2026-10-03

## Problem and evidence

The learner could select an area but could not start. Home intentionally disabled Start when the
server returned no eligible next lesson for the selected goal; it must not substitute an unrelated
lesson. However, its explanation and activation link appeared in a separate lower card. During
lookup it also displayed empty-selection copy, and a saved area missing from the loading catalogue
made the native select appear to choose the whole map.

## Change

- The start/resume card identifies the new-session topic. A confirmed empty selected area/course
  replaces dead Start with a primary Review and activate a lesson link. Areas already supports
  the `area` query parameter, so this opens the selected area's review workflow.
- Saving/checking, failed lookup, and confirmed empty selection have distinct copy. Failed lesson
  lookup retains its retry and does not masquerade as a need to activate content.
- Topic selectors wait for pending preference save/lesson refetch; the saved area remains an option
  while catalogue names are unavailable. Failed names have a Retry topics action.
- Resume preserves the existing session. No lessons are activated automatically and no goal,
  curriculum eligibility, server session semantics or mastery is changed.

## Verification

- Home component tests: 9 passed (4 added: empty-area primary recovery, deferred switch then start,
  failed catalogue preserves selection, failed lesson lookup distinct from empty).
- Full frontend suite: 328 tests / 83 files passed. Final copy refinement rechecked Home 9.
- TypeScript build check and changed-file ESLint passed.
- Four isolated browser journeys passed (390/800/1280px and narrow empty-topic activation).
- Integration lint and production build passed; existing bundle-size/spectrogram warnings remain.
- Independent code and pedagogy reviews found no blockers or majors.
- Live database untouched; fake requests only. No models or paid calls.

## Outstanding

The root agent identified catalogue latency as a separate backend issue. This slice reports
pending state but does not make catalogue queries faster. Owner usability confirmation remains open.
