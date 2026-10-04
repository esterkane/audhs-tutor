# Design foundations: control boundaries and code surfaces

2026-10-04 — Phase10, Stage1a. Production changes are limited to `frontend/src/index.css` and `frontend/src/components/ui/textarea.tsx`. No backend, callbacks, value storage, learning logic or libraries changed.

## Reproduced before editing

Eight isolated browser observations exercised an actual lesson route with a synthetic streamed Markdown response, in explicit light/dark and system light/dark at390/1280px. Narrow cases use the existing large-text preference. A keyboard-entered next question survived pause/resume. Baseline measurement mode collected contrast without enforcing the intended new thresholds; that bypass was removed before committing the final regression tests.

Current Textarea border/card contrast was1.36 light/1.39 dark. System dark mode inherited the light inline-code background, leaving light text at1.08:1 contrast. Explicit dark's more-specific code selector also overrode the intended transparent background for code inside pre blocks. Before measurements: [JSON](../design/evidence/phase10a/before.json), [system-dark screenshot](../design/evidence/phase10a/before-system-dark-390.png).

## Change

Added semantic `control` and `code` colors in the existing theme and both dark-theme paths. Textarea uses `border-control`; decorative borders retain `line`. Inline code uses `--color-code`, avoiding a dark selector override; existing pre/code transparency now works consistently. Values: control light#697380/dark#8993a0; code preserves intended light#eef0f3/dark#2a3038. Existing focus outline, input sizing, props and class override support remain.

## Verification

After: control/card4.81 light/5.14 dark; inline text13.84 light/10.84 dark including system mode. Keyboard focus contrast5.66/6.47 and3px outline retained. No horizontal overflow in tested states. Code-block inner background transparent in all cases. [After measurements](../design/evidence/phase10a/after.json), [dark/narrow](../design/evidence/phase10a/after-system-dark-390.png), [light/desktop](../design/evidence/phase10a/after-light-1280.png). Before/after images inspected.

Original checkout:19 browser tests passed (eight new theme/input/code, two lesson replay/recovery, nine pause/checkpoint/race);10 Session/SessionControls unit tests passed. ESLint, TypeScript and production build passed. Build retains large-chunk and spectrogram worker externalization warnings; unit environment logs its existing canvas getContext limitation. No model or microphone used by these fixtures.

## Remaining scope

This fixes the shared Textarea, not every route-local native textarea/input/select. Screenshot shows the separate explanation-notes field still uses its old boundary. Do not claim all controls or accessibility conform. Full200% zoom, screen reader, forced colors and real audio remain later gates. Park overlap, global density and progress semantics are unchanged. Stage1b next: reproduce primitive label/heading issues before editing; Phase10 is not complete from this slice.

Sanitized checkout: all eight new browser checks passed; publication guard passed.
