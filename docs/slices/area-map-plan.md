# C4: area-scoped map implementation contract

## Observed problem and evidence

The map route currently requests the complete `/api/skills/map` result and renders every node and the complete Mermaid diagram. It offers no area selection. Browsing an area does not establish the scope of this map. `AreaOut.active_lessons` is a count, not membership; filtering titles or source matching terms would fabricate relationships.

The authoritative membership already exists as `SkillNode.area_id`. `kernel/areas.py` uses that field for active lesson counts. `kernel/skill_graph.py` uses it for learning goals, but the map response currently omits it. `goal_scope` also reads learner preferences, so navigation must not call it with implicit saved goals or modify those goals merely to filter a map.

## Small coherent change to implement next

1. Add optional `area_id` to the read-only map endpoint. Validate a supplied area against the existing area catalog. Omitted scope keeps the whole map. An unknown area returns an explicit unavailable state; a real empty area returns an empty scoped map, never the whole map.
2. Select nodes by stored area ID and include the full transitive prerequisite closure. Use only prerequisite edges for that closure. Keep global mastery, memory, unlock and next-selection calculations unchanged. Label included outside-area prerequisites separately; do not call them members of the selected area. Filter the diagram and accessible list from the same node/edge set.
3. Add explicit URL-based area selection to Map using existing area data and semantic tokens. `/map` remains global; `/map?area=ID` is scoped. Refresh, Back and Forward restore scope. Do not silently scope old links from a saved preference. Add an explicit current-area map link to the browse-area control.
4. Keep a visible All areas option, meaningful empty/error recovery and selectable global access even if the area catalog fails. Key read caching by scope. While a new scope loads or fails, never show the prior scope as though it belonged to the new selection.
5. Explain that “next” belongs to the existing learning goal, not a new recommendation computed by map filtering. Learn this retains the existing explicit Home selection/eligibility flow. No session creation, goal writes, mastery updates, model calls or migration are needed.

## Likely files

- `backend/app/api/skills.py`: optional verified scope and response metadata.
- `backend/app/kernel/skill_graph.py`: read-only projection and prerequisite closure.
- Backend map API/kernel tests and generated API types (generate separately in each variant).
- `frontend/src/features/map/api.ts`, `frontend/src/routes/Map.tsx`: scoped query, selector, status and accessible relationship labels.
- `frontend/src/features/areas/BrowseArea.tsx`: explicit scoped-map entry.
- Map component tests and a dedicated area-map browser journey.

## Acceptance gates

Use at least two areas, an empty area, a direct and transitive prerequisite outside the selected area, and an unrelated node. Verify exact scoped node/edge sets, unchanged mastery/unlock/next values, invalid IDs and unchanged global results. Verify no writes during selection; Learn this remains only navigation until explicit start. Test stale/late replies and failed scope changes independently of catalog failures.

Browser journeys must cover desktop and narrow widths, selected-area reload, Back/Forward, keyboard selection and learning link, empty/invalid recovery, rendering/list parity and no horizontal page overflow. Inspect screenshots; run relevant backend/component tests, lint/type checking and production build. Obtain code/state and pedagogy reviews before committing the implementation.

## Phase boundary

This implements the area-map part of C4, not the entire Library or tutor panel. Existing contextual modes/tools have their own recorded verification; human comprehension and end-to-end C3 acceptance remain open. Review-specific lab links are not a new prerequisite invented for C3. Enable audio links only where an authored source relationship exists. Source provenance, generated-answer quality, multi-session recovery and persistent tutor work remain separately scoped.
