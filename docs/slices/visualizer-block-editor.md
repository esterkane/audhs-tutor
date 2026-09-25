# Interactive visualizer block editor

Owner approved React Flow as the next local playground step. Add lazy-loaded draggable canvas and keyboard-equivalent connection selectors to the existing optional diagram. Rewire existing block inputs and visual bindings through the existing validator; reject cycles and invalid targets before mutating the draft. Apply/save remain explicit.
No new API, database, mastery, learner events or model requests. Existing unassessed practice and sensory/low-energy path remain; canvas optional, no animated edges. Node positions are temporary UI state, not preset semantics. Text diagram remains available.
Acceptance: valid replacement updates shared JSON only; invalid/cyclic edits preserve prior draft; keyboard selectors equivalent to canvas connections; output IDs cannot collide with valid node IDs; real browser checks canvas and persistence. New MIT dependency @xyflow/react pinned in package/lockfile. This is the first visualizer block-editor slice, not n8n/RAG execution or adding/removing blocks.

## Verification and review fixes

- 82 frontend tests passed; make lint passed; production build passed (large-chunk advisory remains).
- After review fixes: three connection tests and isolated Chromium journey passed. Journey tests actual node and connector dragging, keyboard inspection, draft-only rewiring, cycle rejection, apply/save/reload, and a valid constructor node ID. Screenshot inspected.
- Code and pedagogy reviews cleared blockers/majors. Clarified Apply vs Save; null-prototype layout avoids inherited keys. Preserve controlled node measurements with applyNodeChanges, fixing invisible nodes caught in browser testing.
- Existing eslint-plugin-jsx-a11y/eslint and openapi-typescript/TypeScript peer warnings remain; no React Flow peer conflict. Canvas is dynamically imported; no hosted services or CDN dependencies introduced.
