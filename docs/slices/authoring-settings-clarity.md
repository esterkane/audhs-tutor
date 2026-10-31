# Authoring setup and hosted spending clarity

The Settings page previously exposed generic authoring enablement and raw cents controls in
addition to the dedicated writing-workspace setup form. It now uses that same explicit form;
no generic authoring preference is rendered. Saving a key remains independent of choosing
OpenAI, changing a cap or making a model request. Other preferences retain their existing controls.

The Models cost view names its ordinary-study cap. Both surfaces explain the actual accounting:
different authoring/study permissions and caps count the same app-wide hosted spending, not
separate additive wallets. This changes neither budget enforcement nor model routing.

Setup reads now have a 15-second deadline and explicit retry. Missing data is unknown, never a
fabricated local mode or zero spending. Cached data is labelled potentially outdated on failure;
key/provider writes require a successful setup read. An authoritative zero cap displays zero,
and choosing local authoring preserves it rather than substituting a five-dollar default.

Verification (isolated learner data; fake key only):
- Full frontend suite: 825 passed across 160 files; additional zero-cap regression passes in
  the final six-test authoring module. The new test was added after the full-suite run.
- TypeScript app and browser types, full ESLint and production build passed; final changed-test
  ESLint and browser types passed.
- Three Chromium setup journeys pass: explicit key save from both Settings and writing,
  unchanged provider/cap, unavailable-status retry with no writes, duplicate-control absence,
  narrow-screen overflow and axe WCAG A/AA checks.
- Full focused upload → research → own writing → Library draft reopen → review → activate →
  reading/notes → pause/resume → feedback/check → recap → Library lesson search passes.
  Assessment uses the explicit uncertainty confirmation path, not certification of model grading.
- Backend, database schema, credentials, histories, model assignments and caps unchanged.

The preceding GitHub run completed all non-browser jobs successfully, but its browser job was
cancelled. It is incomplete, not green. A new publication gets its own exact-head CI run.
Broader tutor accuracy, decoding speed, notebook qualification and other usability-review items
remain open. No hosted inference or Claude consultation is needed for this slice.
