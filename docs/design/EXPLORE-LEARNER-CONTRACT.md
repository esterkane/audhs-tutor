# Explore learner-facing entry contract

Status: next incomplete design slice; architecture finding documented before edits.
Target: complete design-system PDF p10 Explore blueprint.

## Current evidence

The shell's Explore destination is /areas. Areas.tsx is currently an authoring screen:
its introduction asks the learner to review and activate drafts, its area selector
shows course/source-candidate counts, and it displays imported/unmatched document
counts alongside a batch-drafting action. The selected area prioritises prepared
and historical drafts. Source disclosures are already present and must be retained.

AreaOut already provides title, description and active_lessons. Descriptions are
editable source data, not validated learning outcomes. Do not invent outcomes from
course names or equate active lesson counts with demonstrated understanding.
Browse state and learning selection are deliberately separate; browsing must not
change the active session, learning goal, evidence or preferences.

## Smallest coherent next implementation

- Keep /areas and its existing query-location/dirty-edit behavior for authoring and
  old deep links. Add a learner-facing Explore entry using existing area data and
  shared tokens/components, rather than hiding authoring controls inside a renamed
  screen or mounting duplicate editor owners.
- Explore tiles show area title, existing description when present, and honest
  readiness (activated lessons available, or preparation required). Missing
  descriptions receive neutral copy, not fabricated learning promises.
- Opening an area exposes its available concepts/lessons before preparation links.
  Inspect the existing curriculum/skill mappings to establish exact area membership;
  do not reuse fuzzy source matching as a conceptual prerequisite graph.
- Explicit Choose for learning passes through Home's existing selection/readiness
  flow. It never silently replaces an active session or starts an unrelated lesson.
- Keep a visible secondary Prepare material link to existing authoring state.
  Material import counts/unmatched diagnostics remain available under Materials,
  with preserved access to their current data; do not discard diagnostic functions.
- Update shell Explore destination and active-state mapping together. Old /areas
  links, saved authoring locations and edit guards must still work. Document route
  decisions before changing them; no new libraries or learning-kernel logic.

## Likely affected files

New learner Explore route/component; app route table; shell navigation mapping;
existing area/skill query adapters only if required for exact membership; focused
browser tests. Areas authoring is preserved, not wholesale rewritten. Reuse existing
read endpoints where they establish membership; document a read-only API addition
if current endpoints cannot do so without guessing.

## Verification gates

Baseline BrowseArea journeys first. Then empty/loading/error/readiness states;
keyboard tile navigation; desktop/narrow/light/dark layouts; deep link and Back/
Forward; unsaved authoring edits; choosing an empty area without fallback; unchanged
active session while browsing. Read-only browsing must issue no learning writes.
Verify real source-backed concept membership and distinguish unavailable data from
zero lessons. Code/pedagogy review and visual inspection before publishing both repos.

## Membership implementation in progress

GET /api/areas/{area_id}/concepts exposes only teachable SkillNodes whose explicit
area_id matches the selected area, with existing description/success criteria. It
uses the same eligibility predicate as active_lessons; it does not infer membership
from documents or refresh competency. A focused backend test passes for exact
membership, exclusion of a title-only match and vocabulary deck, empty/missing area,
and unchanged event/evidence counts. Mypy passes; import lint issue corrected.
This API foundation is not yet wired into a learner route or published. Next build
the read-only Explore view and verify selection through Home without changing an
active session. Existing authoring remains /areas.

Learner entry implemented in progress: /explore uses area descriptions and exact
concept memberships; activated concept cards expose existing success criteria and
Choose this lesson links into Home. Empty areas do not offer unrelated lessons.
The shell Explore entry points there; /areas remains intact and reachable as Prepare
learning material. Materials remains linked for diagnostics. Two browser tests at
320/1280 pass for keyboard area selection, concept outcomes, Back, empty state,
overflow and no learning writes. TypeScript/lint pass. Still pending: shared BrowseArea
and quick-navigation route reconciliation, error/retry and active-session selection
journeys, visual/dark acceptance, reviews/build and publication.

Navigation reconciliation: global Browse area opens /explore except while already
in /areas authoring, where the existing query/dirty-edit protection is retained.
Explore remembers only local browse history. Quick navigation inherits both Explore
and Prepare learning material from the shared page lists. Six browser journeys pass
for old area-location history, browse history, narrow/light and desktop/dark Explore,
concept failure/retry, empty areas and no learning writes. Lint/build pass (existing
chunk warning); desktop dark screenshot inspected. Code/pedagogy reviews clear.
Remaining before publication: verify Choose this lesson through Home with an existing
session, inspect narrow visual, and complete the final sanitation/snapshot cycle.


2026-10-11: Learner Explore now leads with areas and exact activated concepts, existing
descriptions/criteria, and explicit Home lesson selection. Preparation stays at/areas
with its existing edit guards; browse navigation/history are separate from learning.
Empty areas never substitute unrelated lessons. One backend membership/no-write test,
six navigation/browser checks plus final three Explore checks (including a real active
session preserved during selection), types/lint/build and reviews pass. Light320 and
dark1280 screenshots inspected. No learning-policy changes. Existing chunk warning
and broad human/AT acceptance remain; this does not complete the entire design system.
See docs/design/EXPLORE-LEARNER-CONTRACT.md.
