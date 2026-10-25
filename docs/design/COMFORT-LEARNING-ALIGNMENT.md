# Comfort and learning alignment — 2026-10-25

The owner adopted the brief in docs/agent-handoffs/DESIGN_SYSTEM_BRIEF.md as an authoritative
input and authorized implementation. Its original commit is preserved in ancestry. Apply this
addendum alongside the complete design PDF and navigation/workspace specification, not as a
replacement theme or a diagnosis-driven layout. General claims about AuDHD are hypotheses;
learners choose comfort explicitly. No claim that every learner needs the same sensory treatment.

## Reconciled implementation

- Existing local profile preferences are the single authority for motion, sound, text size,
  system-font selection and break interval. No new cloud store, analytics or font dependency.
- Keep the app's more cautious motion-off default. Legacy reduced_motion=false maps to low
  until a new motion choice is explicitly saved. New off/low/full choices work immediately;
  OS reduction is always the stronger safety ceiling, including live OS changes. This is a
  deliberate reconciliation of the brief's conflicting explicit-override and OS-safety text.
- Existing large text remains 118%; extra-large 131% is additive. Root data-font now describes
  the font family; data-text-size carries size. Default uses the existing bundled Inter;
  readable uses the device's system sans font, without claiming a special clinical benefit.
- Decorative effects remain off and unavailable. Do not offer a misleading enabled setting
  for uninstalled effects. Existing educational plots/notebooks are not decorative CanvasUI.
- Persistent global focus is reversible from the header or Escape; the parking control and
  current learning location stay reachable. Existing session focus and lesson actions remain.
- A small skippable Home hint links to comfort settings without gating entry into learning.
- Break reminders use15/25/40active minutes or off, pause when hidden/idle, and defer while
  text editing or lesson/Ask/authoring generation is active. They never interrupt, end a session,
  claim lost streaks or move focus. Keep learning dismisses; the existing quiet space is linked.
- Existing section-based lesson reading gains an explicit restored-position cue, non-destructive
  Read from the beginning, and reading-location/progress semantics. Backward navigation shows
  the true reading position; it never claims completion/mastery or irreversible progress.
- Research, lesson and Ask answer components expose Sources(n), including zero. No-source
  answers have explicit amber uncertainty text. Quotation counts are not verification scores.
- Preserve the existing deterministic assessment evidence, retry and polite status region.
  Recorded unmet criteria use an amber “Not quite” heading, with the original evidence intact.
  Do not replace rubric evidence with invented mistakes, punitive animation or model grading.

## Token/interaction contract

Reuse canonical Tailwind tokens. No parallel palette; the brief's hex values were illustrative.
Root data-motion, data-effects, data-focus, data-text-size and data-font expose applied comfort.
Motion-off has zero CSS transitions/animations; other modes add no ambient loops or effects.
Motion durations 150/220 ms and movement ceiling 4/8 px are available for later explicit transitions.
Focus is3px with 2px offset, including essential controls. Long prose retains 68ch. Current
opaque text/control pairs are measured in comfort-contrast.json; rendered token tests cover
light/dark, OS themes, narrow layout and code/input states. Decorative separators are not
claimed to meet control-boundary contrast.

## Verification and limits

Verification: full frontend 780 passed; targeted final comfort/source/reading suite and production
build passed. TypeScript and full ESLint passed. Backend Ruff/format/mypy passed; doctor/kernel
focused 29 passed. Claude bridge 33 offline tests passed, including real stdio. Live doctor reports
healthy for local/authoring and exits 2 for a deliberately closed API port, without inference.
Browser evidence: core research/lesson 10 passed; token-theme 8 passed; corrected comfort/header/
keyboard 6 passed; preference read/write/recovery 14 passed; real 200% zoom/segmented 6 passed; evidence-first feedback 2 passed.
These overlap where deliberately rerun after a fix; do not present the sum as unique journeys.
Axe found no serious/critical findings on both comfort settings layouts; existing research,
reading/feedback journeys retain their own accessibility gates. The full backend regression
result is 2,339 passed / 1 skipped. Remote CI outcome is recorded in the private handoff. Synthetic sandbox only for browser
learning flows; no real learner progress, session history or hosted authoring settings reset.

CanvasUI is deliberately not installed: adding it still requires the owner's dependency choice,
licence/API inspection, lazy one-effect gate and actual GPU contention measurements. Effects-on
mount/unmount and tokens/sec comparisons cannot be claimed before an effect exists. No new
runtime three.js dependency. No Safari, Firefox or human NVDA/VoiceOver result is claimed from
Chromium/axe. These remain explicit acceptance gaps, not implied passes. The existing body-
doubling page is a quiet destination, not the proposed timed graphics break screen. Per-section
reading time estimates and broader course-level breadcrumb/resume composition remain separate
bounded follow-up work; do not invent precise timings or rewrite stored learning state here.

Production entry bundle: before 2,031.34kB / 609.36kB gzip; after 2,037.41 kB / 610.48 kB gzip.
CSS before 67.63kB / 16.86kB gzip; after 68.55kB / 17.08kB gzip. No new dependency or effect
bundle. The existing large entry bundle warning remains; this slice is not a loading-speed claim.

Legacy-response follow-up: hide ui.reduced_motion only when the returned specification also
contains ui.motion. Older/offline cached response shapes retain their only motion switch.
The existing320px recovery test exposed this gap; both legacy320/1280 and modern390/1280
comfort journeys then passed (4tests). ESLint and TypeScript passed. No schema/history change.
The bundle figures above describe d0bd787, before this small compatibility predicate.

## Course reading follow-up — 2026-10-25

[Course-reading path slice](../slices/course-reading-path.md) delivers verified manifest course/
section/phase breadcrumbs, active-session subject/skill/activity context, material-version reading
trails and disclosed text-only reading estimates. It preserves all existing bookmark/history keys.
The earlier breadcrumb/timing gap above is superseded by this bounded implementation; a separate
per-course step-selection memory beyond the existing saved route is not claimed. Optional effects
and cross-browser/human assistive-technology acceptance remain as documented.
