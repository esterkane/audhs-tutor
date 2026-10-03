# UX research integration — 2026-10-03

Owner priority: the interface is still confusing. Treat comprehension as an open release gate,
not a solved problem because tests pass. Reconcile this work with R2/R4/R6/R7/R8/R10 and Q learning
experience tasks; do not restart their implementation or replace the app architecture.

## Assessment of the supplied report

The report supplies a reusable audit → prioritize → implement → review → regression loop, not
an audit of current code. Adopt focused journeys, evidence-linked issues, failure-state coverage,
keyboard/reflow checks and dated change records. Its example files, Electron assumption, sample
changelog and persona dialogue are hypothetical and must not be reported as observations.

Adapt these recommendations:
- Use existing React/Vite, Playwright, axe and primitives. No new Selenium/Cypress or analytics service.
- Use WCAG 2.2 AA as the target already chosen by the project. Axe is partial evidence, not certification.
- Simulated personas generate hypotheses only. Do not invent learner testimonials or success rates.
- Prefer concrete task completion, wrong turns and visible save/error/return states to engagement metrics.
  No bounce-rate tracking, NPS collection or covert telemetry is needed for this local personal app.
- Measure actual page/interaction latency with environment and sample count. The report's Lighthouse TTI
  suggestion is outdated: TTI was removed in Lighthouse 10. Do not add a score gate without a baseline.
- Test actual focus, accessible names, contrast and behavior; asserting a CSS color alone is not a contrast test.
- Use short decision/evidence summaries. Prompt templates do not require revealing hidden reasoning.
- Owner authorization covers UX improvements. The document's generic human-approval flow is not an
  additional permission requirement for reversible fixes. Retain normal review and publication policies.

Primary references checked 2026-10-03:
[Nielsen heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/),
[WCAG 2.2 understanding](https://www.w3.org/WAI/WCAG22/Understanding/),
[Lighthouse TTI removal](https://developer.chrome.com/docs/lighthouse/performance/interactive/).

## Current evidence ledger and order

| ID | Evidence and user cost | Next slice / gate |
|---|---|---|
| UX26-01 / R7 | Reproduced Programs narrow view: header + course/step selectors + saved answers + view switch precede the lesson. Multiple navigation levels compete. | Put current topic and lesson first; collapse course switching; one explicit path to full notebook tools. Verify 320px/keyboard. |
| UX26-02 / R4,R7 | Programs source initializes course/section to empty; reload resolves first course/step despite per-step notes being saved. | Restore selected course/step with validated local location; disclose unavailable location/storage; preserve notes. |
| UX26-03 / R6,R7 | Two notebooks exist: guided task starter and whole-course notebook. Current view names do not explain scope or browser-vs-native execution. | Explain each at the choice point, retain starter return, provide explicit return from full notebook. No auto execution/install. |
| UX26-04 / Q2,R7 | Tutor exposes explanation/hint/Socratic/review plus message, reuse policy and technical limits. User reports losing the conversation thread. Source-confirmed control density, fresh browser reproduction pending. | Inspect tutor before/after a reply; separate main conversation from optional questioning and technical detail without hiding provider disclosure. |
| UX26-05 / R7 | Shell says session running while project study has a separate pause. Current title is frontend. | Reconcile navigation/status wording and route titles; explain local study pause vs server session. Verify stopping and resume. |
| UX26-06 / R10 | Global and inline audio controls duplicate status; owner previously could not hear playback. | Test explain/question/tutor playback, visible playing/paused/error, speed/volume and device guidance. No autoplay. |
| UX26-07 / R8 | Tests cannot show owner understands current topic, next action, save location and exit. | Keep owner comprehension gate open after each preview; record actual feedback only. |

First implement UX26-01–03 as the project-study orientation slice. Continue UX26-04, then shell/audio
with their existing reliability gates. Course ingestion, visual explanation and authoring queues remain
open; do not claim material coverage or degree credit from UI navigation.

## Reusable execution prompts

### Audit a learner journey
Read current handoff and this ledger. Select one journey (resume, understand → try → check, notebook
round trip, ask/help/follow-up, or stop/change topic). Inspect current source and rendered desktop/narrow
UI. Record trigger, observed state, expected action and recovery. Classify evidence as reproduced,
source-confirmed, hypothetical or already fixed. Map to existing R/Q IDs. Do not use simulated-user
statements as evidence. Rank by task blockage and lost work before cosmetic concerns.

### Implement an evidenced finding
Use audhs-learning-ux and relevant reliability/evidence skills. Write a bounded slice with ownership,
primary action and acceptance cases. Reproduce behavioral defects before changing them. Reuse existing
components; keep explanation before questions, optional confidence, explicit Socratic mode and reachable
stop. Preserve notes/code/history/provenance across navigation. No new model route or automatic execution.

### Verify and hand off
Run relevant component tests and isolated browser journeys with synthetic content, keyboard navigation,
320px reflow, 200% text, saved-state recovery and service/storage failures. Inspect screenshots and focus;
run axe where applicable. Record exact checks, performance measurements if taken, limitations and the
remaining owner comprehension question. Obtain code/pedagogy review, fix major findings, then publish both
private variants per owner policy. Update this ledger and the shared handoff with the concrete delta.


## Second report: design-system workflow

The later supplied report adds inventory, design tokens and component consistency. Adopt the inventory
and incremental component audit; see [UI-INVENTORY.md](UI-INVENTORY.md). Existing `index.css` tokens,
Button variants, sensory settings and Playwright/axe are the starting point. Do not install a new theme
provider, CSS-in-JS stack or test framework. Its login screen, branches, example props and timeline are
hypothetical, not current requirements or completed work. Existing dual-private publication rules apply.

Corrections before implementation:
- A color token is not inherently accessible: verify foreground/background and component state pairs.
- 16px is a useful design starting point, not proof of WCAG AA. Test content/functionality at 200% text
  enlargement and reflow. [W3C resize-text guidance](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html).
- Do not give every decorative icon descriptive text; redundant descriptions add noise. Informative
  content needs alternatives, decorative images use empty alternatives, and controls need names.
  [W3C decorative-image guidance](https://www.w3.org/WAI/tutorials/images/decorative/).
- Do not claim a fixed percentage of accessibility coverage or 90% real-user task success from automation.
  Coverage percentages, sample schedules and fictional success metrics are not acceptance evidence.
- Prioritize behavior and layout at actual font sizes; pixel snapshots supplement, not replace, keyboard
  and readable-state assertions. No external screenshot/analytics service is needed.

Added queue: UX26-08 / R7 — audit used utility names against declared tokens, including `bg-surface`
and `border-border` in program tutor controls; verify state contrast before changing shared primitives.
Then check form/status consistency, long labels, focus, dialog exit and navigation across inventory groups.
Each slice records a concrete before/after journey and actual checks rather than a bulk search/replace.

## First slice status

UX26-01–03 implemented and tested in `docs/slices/project-study-orientation.md`: 309 frontend tests,
eight browser journeys, scoped main-content axe, 320px/200% text, lint/build and reviews.
This is an implementation gate, not owner comprehension approval. UX26-04–08 remain open.
