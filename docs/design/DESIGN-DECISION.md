# Design direction recommendation — Phase 8

2026-10-04. Recommend **A — Quiet Workspace** as the default reading/session direction for the later implementation plan. This is an evidence-informed design recommendation, not owner approval, a measured learning benefit or permission to replace production flows wholesale. Preserve contextual help and existing notebook/visualizer workspaces; do not force every task into a narrow reading column.

## Comparison basis

The [three prototypes](../../design-experiments/ux-directions/README.md) share content, information architecture and fixture actions. Their differences are layout and emphasis. Re-ran nine isolated checks at 320/390/1280px: all passed, including keyboard pause/resume/Undo, retained temporary notes, explicit help focus, initial axe checks and no page overflow. Focused ESLint passed. Production application and learning logic were not modified.

Added layout measurements to the existing probe. Values below are CSS pixels in the initial light-mode fixture with viewport height 900. They include the same prototype comparison toolbar and navigation. They are not production timings, reading efficiency or human effort measurements. Shorter pages alone are not necessarily better.

| Direction | Width | Document height | Primary action top | Help panel top |
|---|---:|---:|---:|---:|
| A Quiet | 1280 | 1347 | 771 | 1033 |
| B Structured | 1280 | 1336 | 734 | 1021 |
| C Canvas | 1280 | 1162 | 822 | 390 |
| A Quiet | 390 | 1825 | 1181 | 1495 |
| B Structured | 390 | 1992 | 1294 | 1625 |
| C Canvas | 390 | 1978 | 1280 | 1611 |
| A Quiet | 320 | 1986 | 1290 | 1604 |
| B Structured | 320 | 2164 | 1466 | 1797 |
| C Canvas | 320 | 2150 | 1452 | 1783 |

Raw measurements: [A desktop](evidence/phase8/quiet-1280.json), [A narrow](evidence/phase8/quiet-320.json), [B desktop](evidence/phase8/structured-1280.json), [B narrow](evidence/phase8/structured-320.json), [C desktop](evidence/phase8/canvas-1280.json), [C narrow](evidence/phase8/canvas-320.json). The evidence directory also contains 390px measurements. Phase 7 contains inspected screenshots of every direction.

## Scoring matrix

Scores are reviewer judgments, not test-derived percentages: 1 poor fit, 2 material weaknesses, 3 workable with unresolved limits, 4 good fit, 5 strongest fit for this criterion. Weights reflect the owner's emphasis on cognitive clarity, predictable learning and accessibility. Higher complexity score means lower implementation risk/effort. Accessibility and interruption scores are deliberately equal because the prototypes share semantics and temporary-state behavior; none proves full accessibility or real delayed re-entry.

| Criterion | Weight | A Quiet | B Structured | C Canvas | Reason / evidence limit |
|---|---:|---:|---:|---:|---|
| Cognitive load | 20% | 4 | 3 | 3 | A has less competing surface chrome; C makes help visible but splits desktop attention. Inferred from hierarchy, not a measured cognitive score. |
| Accessibility | 15% | 3 | 3 | 3 | Same initial axe/keyboard results; dark mode, text zoom, screen reader and complex production states remain open for all. |
| Clarity | 15% | 4 | 4 | 4 | Identical topic, worked example, next action and explicit prototype/save scope. B emphasizes outline; C emphasizes help. No comprehension comparison yet. |
| Responsiveness | 10% | 4 | 3 | 3 | All reflow; A produces shorter narrow documents and earlier primary action in this content sample. All still require scrolling. |
| Interruption recovery | 15% | 3 | 3 | 3 | Same note retention/pause simulation. No real server persistence or elapsed-week test in these prototypes. |
| Visual hierarchy | 10% | 4 | 4 | 4 | A emphasizes prose, B phase grouping, C adjacent help. Different strengths rather than an objectively universal winner. |
| Implementation complexity | 5% | 5 | 4 | 3 | A needs least new layout orchestration. C requires careful task-specific side-panel and narrow-screen behavior. All must integrate real recovery state. |
| Current architecture fit | 10% | 4 | 5 | 4 | B most closely resembles existing card primitives; A reuses tokens with fewer containers; C resembles wide workspaces but should not be imposed on all routes. |
| **Weighted result /5** | **100%** | **3.75** | **3.50** | **3.35** | Narrow recommendation, not a decisive measured superiority. |

The margin between A and B is small. Raising B's cognitive-load and responsiveness judgments by one point each would make B lead (3.80). No precision beyond this transparent decision aid is warranted. The recommendation rests on the user's repeated complaints about confusing, competing controls and A's simpler reading surface, while retaining explicit orientation from the shared IA.

## What the recommendation adopts

- A's single content-first reading surface for explanations and feedback, using existing tokens and primitives.
- The shared topic/activity orientation, obvious primary next action and reachable pause/help.
- Explicit save/response/error wording and contextual source disclosure from the common specification.
- Existing wider task layouts for notebook/visualizer work. C remains a reference for contextual help placement in those tasks, not a second automatic learner mode.

Do not copy the prototype's temporary-state script or sample content into runtime logic. Do not add a preference that asks the learner to choose A/B/C before studying. Do not remove review, confidence options, advanced settings, models, import, correction, voice or saved answers. The prototype outline is not an approved replacement for the server's learning phases.

## Conditions before accepting production changes

**Help reachability:** A's help panel starts below the initial desktop viewport and much farther down on narrow screens. Keep the in-context help action adjacent to the work; ensure its result is visible and focus returns sensibly without losing the answer. Compare an inline response or existing contextual surface during implementation rather than merely moving the full toolbar upward.

**Orientation without extra setup:** maintain a compact current activity indicator but do not force another planning screen or introduce new progress metrics. The existing mastery concern HR-01 requires its own learning-model investigation.

**Real state:** verify actual pause/resume, interrupted grading, request identity, notebook checked snapshots and storage failure. Prototype note retention does not substitute for those contracts.

**Accessibility and sensory settings:** check themes, zoom, keyboard, screen reader, focus visibility, existing text/density preferences and real voice controls before broad rollout. Fix the observed Park overlap without covering content with another fixed control.

**Human validation:** ask the owner to identify the current topic, next action, saved state and recovery path without coaching once a bounded real-flow slice is available. A preference change based on that observation should update this decision rather than defend the matrix. Do not claim that a design direction serves a diagnosis better.

## Deferred choices and next step

No new navigation, production theme, library or learning algorithm has been implemented. The next phase is **Phase 9 implementation planning**: explicit file/component scopes, risks, UX outcomes and tests, beginning with existing primitives and truthful states, then bounded learning/navigation changes. Prototype comparison is complete as an expert review; human acceptance and the broader redesign remain incomplete.
