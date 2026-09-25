# Visualizer signal flow

Offer an optional, collapsed signal-flow diagram of the validated editor draft, with explicit per-edge rows and separate visual bindings. Selecting a block opens its existing local explanation.
Label unapplied connections; invalid JSON never shows stale connections. Independent constant/time sources must not imply audio dependencies. No new API, schema, learner state, events, mastery or model calls; this remains unassessed practice.
Use native keyboard buttons and text equivalents for arrows, wrapping on small screens. No animation, sensory or mode changes; existing low-energy path remains.
Acceptance: dependency and output edges accurate, independent sources honest, selection accessible, invalid/draft/applied behavior covered by component and isolated browser tests.

## Verification and review fixes

- Dependency/output edges and independent sources: two SignalFlow component tests pass, including axe.
- Selection and invalid draft: isolated visualizer Chromium journey passes; screenshot inspected.
- Full frontend: 79 tests passed. make lint passed; after wording fixes focused tests, browser journey and frontend lint/types passed again.
- Code review: no blocker/major. Pedagogy review caught energy being shown as used by rings; explicitly labeled unused, with component/browser regression assertions. Final re-review: ship, no blocker/major. Clarified that only paths to outputs used by the selected style can affect the visual.
- Backend/API unchanged; no generated types or migration needed. Unassessed local exploration does not schedule review or write learner events.
