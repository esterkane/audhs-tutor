# Shared typography alignment

2026-10-11 — Complete Design System p5. Shared semantic rem tokens now establish interface14px, Markdown prose16px/26px and code13px/20px. Existing local Inter/Roboto Mono and118% large preference remain. Explicit prose sizing prevents small parent UI containers shrinking explanations. No content, assessment, routing or model behavior changes.

The new320px/200%-root-text browser check exposed741px document overflow from the lesson's implicit single-column grids. Both Session grids now use minmax(0,1fr), so long code stays within its scroll container. This is a layout correction, not clipping or removal of content.

Evidence: two pre-change long-reading journeys passed. Final14 browser journeys passed: exact computed type/line-height and118% scale in320/1280 light/dark;200%-root-text overflow; keyboard focus; existing reading/question/feedback-return, Home resume and Preferences controls. Inspected320/light and1280/dark reading screenshots. All610 frontend unit tests across119 files passed after the typography change; final layout-only correction verified by browser journeys. Targeted ESLint and production type/build passed. Code/pedagogy reviews found no blockers or majors; code reviewer also checked the grid fix. Existing bundle-size warning remains.

Remaining: per-screen semantic heading adoption, custom editors/visual labels, unwrapped long-form text, actual browser zoom, assistive-technology and human readability acceptance. Representative checks do not establish complete application conformance.
