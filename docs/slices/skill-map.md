# Slice: skill-map (Stage 2)

**Story.** The learner sees the whole map first: every node with mastery (computed), memory (items, due, retrievability), unlock state and the suggested next node; they choose what to learn.
**In/out.** `kernel/skill_graph.map_view` (+ `to_mermaid`), `GET /api/skills/map` → nodes, edges, Mermaid source. `Map` route: Mermaid picture (strict security level) plus an accessible list with the same data and a "Learn this" action (disabled when locked). Header link "Skill map".
**Mode/energy.** None; the map never auto-navigates.
**Accessibility.** The SVG is `aria-hidden`; the list is the primary, keyboard-reachable representation.
**Verified by.** `tests/test_stage2_kernel.py::test_representation_cache_and_map`, `tests/test_stage2_api.py` (map endpoint), `frontend/src/routes/Map.test.tsx`; rendered live in the browser pane.
