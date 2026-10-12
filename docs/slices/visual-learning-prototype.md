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
