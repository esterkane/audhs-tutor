# Phase 7 — three isolated visual directions

Open [index.html](index.html) locally in a browser. The comparison selector changes layout without discarding the current demo note. No build, backend, installation or network is needed. These are fixture prototypes; navigation destinations are clearly labelled previews, not production pages. Refresh resets all demo state. No audio, grading, model call or database persistence is implemented or implied.

All three share the Phase5 Home/Learn/Library/Progress/Settings architecture, one original lesson, worked example, practice note, simpler/detail help, source disclosure, pause/resume and reversible clear label. One document and interaction script serve all directions; only layout selectors change. Learning logic is not duplicated. Understand/Try/Reflect is a visual outline, not an implemented session-state machine. Real course/project/assessment logic remains in the app.

## A — Quiet Workspace

**Description/layout:** restrained single reading column, little card chrome, inline activity outline; contextual help follows the content.

**Rationale:** give the explanation and worked example visual priority, using the existing system font and neutral palette.

**Strengths:** low visual competition; readable long-form content; simple mobile adaptation. Component examples: borderless lesson, inline outline, source disclosure, secondary help buttons.

**Risks:** help is below the reading content; repeated scrolling can raise re-entry cost. Explicit help now focuses its resulting heading so the update is findable. Minimal chrome must not make status invisible.

**Target behavior:** sustained reading with occasional contextual questions, not a diagnostic learner category.

## B — Structured Learning

**Description/layout:** left activity outline and accent-topped lesson surface, followed by a clearly separated help card. On narrow screens the outline becomes a wrapping row.

**Rationale:** make position and grouping explicit without inventing mastery percentages.

**Strengths:** stronger phase orientation and predictable boundaries; existing card/button vocabulary maps readily to production. Component examples: step panel, primary next action, bordered help card.

**Risks:** more containers and an extra column compete with the explanation; the step list can imply enforced sequencing. It is labelled an outline here and does not implement new phase transitions.

**Target behavior:** learners seeking explicit structure and recognizable return points.

## C — Adaptive Canvas

**Description/layout:** shared outline above a reading/practice surface and adjacent contextual help panel. Single-column stacking on narrow screens.

**Rationale:** keep material and help together for iterative work, potentially useful for notebook/explanation workflows later.

**Strengths:** desktop help is immediately discoverable; one task stays visible beside its explanation controls. Component examples: work surface, contextual side panel, optional details within each.

**Risks:** competing columns can split attention and reduce reading width. Mobile still requires scrolling. “Adaptive” names a layout direction, not automatic personalization, content inference or model-driven layout.

**Target behavior:** alternating between work and explanations while retaining the same target.

## Shared implementation boundaries

Prototype-only CSS uses semantic variables mapped to the existing palette and spacing system. The stronger control boundary is a prototype specimen, not a production token migration. It currently demonstrates light mode only. Dark/system themes, actual voice, streaming, real persistence, notebook execution, full nav destinations and learning-policy integration remain production acceptance work. No new library was added; existing Playwright and axe run verification.

Deliberately limited capability is labelled in the prototype: navigation previews describe existing destinations and return to the same note; Listen options explains that no audio plays; practice is an ungraded note; saving a clear label does not claim mastery. Do not deploy this HTML as a replacement for the application or report these fixture checks as production usability improvement.

## Verification

From the repository root:

```sh
AUDHS_DESIGN_REVIEW=1 pnpm --dir frontend exec playwright test --config design.playwright.config.ts --reporter=list
pnpm --dir frontend exec eslint e2e/design-directions.spec.ts design.playwright.config.ts
```

The standalone config starts no backend and intercepts the sole page request with local HTML. All three directions are exercised at320/390/1280px. Checks cover overflow, initial axe WCAG-tag violations, keyboard practice/pause/resume/Undo, note preservation across direction/navigation changes, visible help, focus on explicit help and current navigation state. A passing run does not prove human comprehension, full screen-reader support, dark mode, text zoom or complete task flow. The opt-in file is skipped in ordinary production journeys.

Initial six checks passed. Visual review found help could update below the viewport and navigation previews retained the Learn highlight; both corrected within the prototype before the expanded nine-check run. Production files were not changed. Screenshots under `docs/design/evidence/phase7` show initial sample layouts. The next phase is comparison/scoring and a documented direction recommendation; no winner is declared in Phase7.

Final expanded run: nine checks passed; focused ESLint and inline-script syntax check passed. Desktop and320px screenshots inspected for all three directions. Narrow layouts retain controls but remain long; human task completion and preferred density are still unverified.
