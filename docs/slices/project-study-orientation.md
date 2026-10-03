# Project study orientation (UX26-01–03, R4/R7)

Story: a returning learner immediately sees the selected project step, its explanation and next action,
can deliberately change course, and understands the difference between a small task starter and the full
course notebook. Temporary location is browser-owned; learner progress stays server-owned.
No schema, model, event or grading change. No native notebook starts or code executes without a click.
Keep all notes and existing notebook drafts; keyboard focus follows explicit navigation; sensory/mode
preferences and optional confidence remain unchanged. See docs/UX-RESEARCH-INTEGRATION.md.

Acceptance: non-first course/step survives reload; stale location and denied storage are explicit;
course picker is secondary; selected title and next action remain visible; full-notebook view has an
explicit return preserving lesson phase/notes; task starter retains existing checked-results return.
Verify desktop, 320px, 200% text, keyboard, axe and existing tutor/notebook journeys. Reviews pending.

## Delivered and verified — 2026-10-03

Current course/step and explanation now precede secondary controls. The chooser is collapsed;
full-course notebook tools are distinct from the small task starter and have an explicit return.
Course/step/view location survives reload with stale-location and storage-failure notices. Existing
lesson phase/notes stay mounted during notebook view changes. Hidden native-lab status polling stops.
No setup, installation, code execution or progress write happens automatically.

A failing component test reproduced non-first course/step loss before the fix. Final component suite:
309 tests / 80 files. Eight isolated Playwright journeys passed: desktop/narrow answer feedback,
chunked lesson recovery, explicit lab launch, desktop/320px orientation+return, and real local task
notebook execution with checked-results return. Orientation checks included keyboard focus, 200% text,
no page overflow and axe AA-tag scan of the main content. Screenshots inspected; live Programs narrow
view inspected without changing learner work. ESLint and production build passed. Existing bundle-size
warning remains. No fresh backend test claim: this slice changes no backend code.

Browser testing caught a delayed requestAnimationFrame focus action interfering with the following
keyboard interaction. Replaced with commit-time layout-effect focus; final journeys passed. Code review
cleared, including the focus follow-up; pedagogy review's save-wording minor corrected.

The two research reports are reconciled in UX-RESEARCH-INTEGRATION.md with an actual UI inventory.
Shared UX skill guidance now requires rendered-journey evidence and separates owner comprehension
from automated checks. Codex skill validation passed.

Limits: location is browser-local, not cross-device; per-step notes retain existing storage behavior.
Owner comprehension, manual screen-reader/400% browser-zoom checks and full-platform accessibility
remain open. At extreme text sizes the shell/floating controls still consume substantial space;
handle in UX26-05/08, not as a claim of conformance from the scoped axe scan. Next: tutor interaction
clarity (UX26-04), then shell/audio and shared token/control consistency. No learner content migrated.
