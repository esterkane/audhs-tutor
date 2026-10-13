# Learner-scoped skill graph reads

Skill graph reads now default to shared nodes and accept explicit learner scope.
Next-skill ranking, goal traversal, map rendering and explicit selection use that
scope before reading nodes or edges. Both endpoints must be visible for an edge to
appear. Direct foreign/missing skill IDs produce the same unavailable behavior.
Learning-object reads through skill_graph also inherit node access.

The skill list/detail/map/evidence/bookmark API passes the current learner. A foreign
bookmark request is rejected before preference writes. An invalid hidden prerequisite
keeps its target locked rather than disappearing from unlock checks. The old final
order[0] fallback is removed: it bypassed the planner's no-unlocked-result decision.
The existing lowest-mastery choice among unlocked nodes remains unchanged.

No private activation or producer is enabled. Other direct ORM consumers, representation
reads, caches and ownership constraints remain pending under PRIVATE-LESSON-ACTIVATION.
This slice is not app-wide isolation. No mastery thresholds, assessment qualification,
model calls or successful shared lesson selection rules are changed.

## Verification
Focused kernel and HTTP tests cover shared/own/foreign visibility, map and Mermaid,
edge filtering, goal selection, direct selection, inherited objects, no-scope denial,
foreign evidence/bookmark denial without writes, and hidden-prerequisite locking.
Existing area-map tests are included. Code/pedagogy review found no blockers or majors.
Full backend suite: 1,581 passed. The three focused graph/area tests also pass after adding the final locked-fallback assertion. Lint/types pass. No frontend visual changes;
existing browser evidence is reused rather than re-running unrelated journeys.

## Next consumer pass
Remaining graph callers needing explicit scope include kernel/exercises and areas;
orchestrator/tutor, tools and playground; API exercises, challenge, areas,
representations and sessions. Their default is now shared-only, so private content
fails closed rather than becoming usable prematurely. Direct ORM access requires a
separate audit; this call-site inventory is not exhaustive security evidence.
