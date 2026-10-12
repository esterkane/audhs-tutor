# Visual learning prototype — data leakage

2026-10-12. Learner changes fitting scope/held-out values to see whether evaluation
information influences preprocessing, then answers a transfer question. Temporary
state only, no learning events or mastery claims. All modes share calm static visuals;
text equivalent/native controls work without dragging, motion or model inference.

Architecture and all13 retained authoring candidates: ../research/visualization-technologies.md.
Prototype /playground/visual-learning, linked from Coding playground. No dependencies
added. Existing React Flow is reused lazily. No DB/curriculum/model changes.

Evidence:4 unit tests (numeric invariance/invalid input/renderer fallback); desktop1280
and narrow390 browser flows include slider keyboard input, select-to-slider Tab,
radio/check keyboard activation, incorrect/correct feedback, reset, return, no overflow
and axe main-content scan. Runs use reduced-motion via shared Playwright config;
renderer always disables animation. No claim of full physical screen-reader acceptance.
Lint/types/production build pass. Initial axe found attribution contrast; corrected
with semantic tokens and retested. Visual inspection caught an edge curve clipping;
straight edges avoid out-of-bounds curves. No unrelated screen redesign.

Bounded code/pedagogy review: no blockers/majors; fixed missing train-to-transform
edge, lazy-route mismatch and candidate count; added sequential Tab check. Graph
has equivalent prose and numerical values; no generated scripts/data accepted.
Unified persisted visual schema is proposed, not implemented by this static prototype.

Build before final edge-only adjustment: route6.19kB/gzip2.51kB; graph1.01kB/gzip0.62kB
plus0.13kB CSS. These exclude shared React Flow chunks and are not full dependency
cost. Existing main chunk warning remains (~1.865MB/gzip565.58kB). Package unpacked
sizes in research are not browser bundle sizes. Future real-object binding, authored
version storage, generated-spec validation, human comprehension/transfer comparison,
screen-reader acceptance and broader subject prototypes remain open.


## Reusable local renderer and optional part help — 2026-10-12

Extracted RelationshipGraph from the leakage adapter. Trusted local graph data,
deterministic positions, React text rendering and existing design tokens; no new
library, network lookup or model call. Learners can optionally select a diagram part
for an explanation. The selection survives fit-scope/value changes and its explanation
updates from current values. Missing selected nodes show the placeholder, not stale
explanation. The math, transfer assessment and temporary/no-mastery policy are unchanged.
This render input is not an API response or the full visual.v1 contract: a later
adapter must validate bound server specifications before passing a safe projection.

Evidence: existing baseline journeys passed before edits;5 focused unit tests passed;
targeted ESLint, TypeScript and production build passed (existing large-chunk warning).
Final390/1280 sandbox journeys passed in8.5s, including keyboard type-ahead selection,
mode changes retaining/updating help, incorrect/correct transfer feedback, reset,
return, no horizontal overflow and zero main-region axe violations. Native-popup
Home/Space+arrow sequences did not select in this headless macOS run; the final test
uses native type-ahead plus Tab, rather than claiming those failed sequences worked.
Both final screenshots inspected. Independent bounded static review: no blockers/majors.

Remaining: live visual.v1 endpoint/storage integration, full source binding and
semantic acceptance, real assistive-technology acceptance, and larger-graph layout.
The narrow graph is intentionally backed by full-size text help; fixed-height layout
is only verified on the four-node prototype. Page prose has some repeated flow
explanation to retain the existing renderer-failure alternative; consolidate only
with fallback coverage. No claim of complete visualization platform delivery.
