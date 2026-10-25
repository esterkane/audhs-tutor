# Design system brief — audhs-tutor

Source: Claude secondary review, 2026-10-25. Put this file at `docs/agent-handoffs/DESIGN_SYSTEM_BRIEF.md`.
Status: recommendations, not verified against the codebase. The reviewer had no access to app source.
Codex owns implementation and must check every assumption here against the real repo first.

## Rule that governs everything

Motion only happens when the student does something, is brief, can be switched off, and never sits behind text the student is reading.
AuDHD learners need novelty and quick reward (ADHD) and predictability with low sensory input (autism). Comfort settings come first; effects are an optional extra.

## Phase 0: Discovery (read-only, then stop for approval)

1. Fill `docs/agent-handoffs/PROJECT_FACTS.md`: framework, styling approach (CSS modules / Tailwind / CSS-in-JS), existing theme or token files, test runners (unit, component, e2e), a11y tooling.
2. List the real screens and map them to: home, topic select, lesson, quiz/feedback, answer-with-sources, settings.
3. Find where "model is generating" state lives, and whether the local LLM runs on the same machine/GPU as the browser (WebGPU in-browser, Ollama/llama.cpp server, remote).
4. Find where per-user preferences are stored today, if anywhere.
5. Report findings plus a plan for Phases 1–3. Do not edit yet.

## Phase 1: Comfort preferences (no new dependencies)

Add one preferences module, stored locally on the device only (no analytics, no server sync unless an existing local profile store already exists).

| Key | Values | Default |
|---|---|---|
| `motion` | `off` / `low` / `full` | `off` if OS `prefers-reduced-motion: reduce`, else `low` |
| `effects` | boolean | `false` |
| `sound` | boolean | `false` |
| `textSize` | `md` / `lg` / `xl` | `md` |
| `font` | `default` / `readable` | `default` |
| `focusMode` | boolean | `false` |
| `breakReminderMin` | `0` (off) / `15` / `25` / `40` | `25` |

- Reflect them on the root element: `data-motion`, `data-effects`, `data-focus`, `data-text-size`, `data-font`. CSS reads these attributes; components do not re-check the OS setting themselves.
- Listen for changes to the OS reduced-motion setting. If the user never set `motion` explicitly, follow the OS.
- Settings panel reachable from the persistent nav in one click. Every control has a visible label, works by keyboard, and applies immediately.
- First run: one skippable screen with motion, text size and effects. "Skip" keeps the defaults.

Acceptance: values survive reload; OS reduce → motion `off` on first load; panel passes axe with no serious violations; Tab order is logical, and keyboard focus is visible everywhere.

## Phase 2: Design tokens

Create one token file (adapt to the project's styling system; if Tailwind, map these into the theme instead of duplicating). Verify every text/background pair reaches WCAG AA (4.5:1 body, 3:1 large text and UI) with a contrast checker before merging. The values below are a starting point.

```css
:root {
  /* colour: soft, low saturation, never pure white page background */
  --color-bg: #F6F7F5;
  --color-surface: #FFFFFF;
  --color-text: #1F2933;
  --color-text-muted: #52606D;
  --color-primary: #3B6E8F;
  --color-success: #2F7A55;
  --color-hint: #8A5A00;      /* "not quite" feedback; amber, not red */
  --color-border: #D9DEE3;
  --color-focus: #1D4ED8;

  /* type */
  --font-body: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-readable: "Atkinson Hyperlegible", system-ui, sans-serif;
  --text-base: 1.0625rem;     /* 17px */
  --leading: 1.6;
  --measure: 68ch;
  --scale: 1.25;

  /* space & shape */
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-6: 24px; --space-8: 32px;
  --radius-control: 8px;
  --radius-card: 12px;
  --shadow-card: 0 1px 2px rgb(16 24 40 / .06), 0 2px 8px rgb(16 24 40 / .06);

  /* motion */
  --dur-fast: 150ms;
  --dur-base: 220ms;
  --ease-out: cubic-bezier(.2, .7, .2, 1);
  --move-max: 8px;
}
:root[data-motion="low"]  { --move-max: 4px; }
:root[data-motion="off"]  { --dur-fast: 0ms; --dur-base: 0ms; --move-max: 0px; }
:root[data-text-size="lg"] { --text-base: 1.1875rem; }
:root[data-text-size="xl"] { --text-base: 1.3125rem; }
:root[data-font="readable"] { --font-body: var(--font-readable); }

/* dark: same token names; also wire to the app's existing theme switch if one exists */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-bg: #15191D; --color-surface: #1E2429; --color-text: #E6E9EC;
    --color-text-muted: #A7B1BA; --color-primary: #8CC1E0; --color-success: #7FCBA4;
    --color-hint: #E7B65C; --color-border: #333D45; --color-focus: #93B4FF;
  }
}
```

Rules:
- Animate `opacity` and `transform` only. No animation over 300ms, no looping animation, no parallax, no autoplaying video or sound.
- Text: left-aligned, never justified, no long italic passages, line width ≤ `--measure`.
- If the readable font is self-hosted, ship it locally (no third-party font CDN, for privacy).
- `:focus-visible` outline: 3px `--color-focus`, 2px offset, on every interactive element.

Acceptance: no hard-coded colours left in the touched components; contrast report saved in the PR description; `data-motion="off"` produces zero CSS transitions (check computed `transition-duration`).

## Phase 3: Learning UX components (plain HTML/CSS, no WebGL)

1. **Lesson card**: one concept per card; header shows "Step 3 of 5" and an estimated time; a single primary action ("Next"). Progress shown as dots or a bar that never moves backwards visually.
2. **Where am I**: persistent breadcrumb `Topic › Lesson › Step`. Navigation stays in the same place on every screen.
3. **Resume on topic switch**: store the last step per topic. On return, show "Continue at step 3" plus "Start over". This is the key test for topic switching.
4. **Feedback**:
   - Correct: check icon, one short sentence, and optionally a single small Ripple when effects are on (Phase 4).
   - Incorrect: "Not quite", one hint, and a retry. Amber `--color-hint`, never red-only, no shaking, and no score penalty animation.
   - Announce feedback in an `aria-live="polite"` region; never move focus unexpectedly.
5. **Answer with sources** (grounding): every model answer shows a "Sources (n)" control that expands to the cited passages. Show a plain-language uncertainty label when retrieval confidence is low or there are no sources ("I couldn't find this in your materials"). Never show an answer without sources styled the same as a grounded one.
6. **Focus mode**: hides the sidebar and secondary chrome, leaving the card plus breadcrumb. Toggle in the header.
7. **Break reminder**: after `breakReminderMin` minutes of active time, show a non-modal, dismissible note. Never while the student is mid-answer or the model is generating. Links to the optional break screen.
8. **Streaks/rewards**: if any exist, remove "streak lost" or loss-framed messaging. Rewards are brief and quiet.

Acceptance: unit tests for resume-per-topic and the break-timer rules; the feedback region announces in a screen reader smoke test (NVDA or VoiceOver); focus mode keeps every lesson action reachable by keyboard.

## Phase 4: Optional CanvasUI effects (needs user approval to add dependencies)

Only these components, only behind `effects === true && motion !== "off"`:

| Component | Where | Settings |
|---|---|---|
| Ripple | Correct-answer badge only (a small element, not the lesson text) | `interval: 0` (no ambient ripples); one splash per correct answer |
| Ink Object | Topic-select header or mascot | Static asset per topic; no cursor-follow if motion is `low` |
| Liquid Object or Frost | Break screen only, which the student opens themselves | 60–120 s timer, then "Back to lesson" |

Never use: Glitch, VHS, Blaze, Flame Wrap, Glyph Rain, Force Field, Laser, Particle Scroll, Particle Reveal, Decrypt Reveal, Asciify, ASCII Sweep, Retro Dither, Displacement, Shatter, Cloth, Droplets, Bubble, Magnify, Grid, Hex Float, Bend, Peel, Clouds, Canvas. Never wrap lesson text, quiz content or model answers in any html-in-canvas effect.

Implementation:
- Install per component with `npx shadcn@latest add @canvas-ui/<name>-react` (or the vanilla/Vue/Svelte build matching the stack). These are copied single files: read each file, record the source URL, and check the licence before committing.
- Build an `EffectGate` wrapper that:
  - renders the effect only when the preference gate passes, the model is **not** generating, and WebGL2 is available; otherwise it renders a static fallback (plain icon or image);
  - loads the effect with a dynamic `import()` so three.js stays out of the main bundle;
  - allows at most one mounted effect app-wide (simple global counter or context);
  - unmounts the effect (calling its `destroy()`) when generation starts, on route change, and when preferences change.
- Liquid Object only stops its floating rotation under reduced motion; its fluid still reacts to the pointer. The gate must therefore not mount it at all when motion is `off`.

Acceptance: with effects off (the default), no `<canvas>` from CanvasUI exists in the DOM and three.js is not loaded; starting a generation removes any mounted effect within one frame; the main bundle size does not grow by more than a few KB (report before/after).

## Phase 5: Verification (report real results)

- Unit: preference defaults (OS reduce → `off`), persistence, explicit choice overrides OS, resume-per-topic, break-timer suppression while answering or generating.
- Component: feedback uses `aria-live`; incorrect state is not red-only; focus outline visible.
- E2E (Playwright or the project's runner):
  - `reducedMotion: "reduce"` → no effect canvas on any screen;
  - effects on → Ripple mounts on a correct answer and is gone afterwards;
  - effects on, start a generation → effect unmounts.
- a11y: axe on home, topic select, lesson, feedback, settings → zero serious/critical violations.
- Performance: if the model runs locally on the same machine, measure tokens/sec on a fixed prompt with the break-screen effect open vs closed (3 runs each, report the median). If it drops noticeably, keep effects to screens without generation (which the gate already enforces) and say so.
- Cross-browser: Chrome, Firefox and Safari. The fallback must look deliberate, not broken.

## Order and approvals

Phase 0 → report → approval → Phases 1–3 (one branch, small commits only if authorised) → report → approval to add dependencies → Phase 4 → Phase 5 report.
Ask before: installing packages, adding fonts, changing stored-data formats, commits, pushes and merges.

## Final report (AGENTS.md format)

**Delivered / Files / Verified (commands + real outcomes) / Risks / Claude review / Approval needed.**
Include the contrast table, bundle-size before/after, and the tokens/sec numbers if measured.
