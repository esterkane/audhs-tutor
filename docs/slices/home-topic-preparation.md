# Home: prepared topic to first session

A selected area can have imported material and a generated draft but no activated lessons. In that
state the planner intentionally returns no next lesson. The former Home action led to another area
selection/review screen, leaving the learner without a clear path to Start.

Home now previews the selected area's generated draft lessons and links directly to that draft in
Learning areas. Interrupted, rejected and unrelated drafts are excluded from the shortcut. The draft
editor still requires explicit Activate lessons; return to Home then enables the existing Start session
flow. No model call, automatic activation, assessment evidence or unrelated-topic fallback is added.
Draft lookup failure has a retry and retains the area review fallback. Ready topics do not mount the
preparation query. Area/draft deep links resolve only inside the selected area's drafts.

Validation (2026-10-03): Home/Areas/Curriculum:23 component tests passed in both variants; TypeScript and targeted ESLint passed.
The integrated original production build passed (existing bundle-size warnings remain).
Five isolated browser journeys passed: ready→empty→ready selection, long-label reflow at320/390px,
and explicit draft review→activation→Home→Start at390/1280px. Those activation/session mutations use
synthetic intercepted API fixtures, not the learner database. Live Home was checked read-only and
showed its selected topic's prepared lessons. Independent code and pedagogy reviews found no blockers
or majors. The owner's comprehension check remains open. This does not activate all topic drafts or
certify their content quality.

Existing limitation: Areas initializes URL selection on mount; same-route query-only navigation is
not a newly supported workflow. The Home→Areas handoff mounts it with the requested selection.

CI follow-up (2026-10-03): full remote browser run had72 passes and two Home fixture failures after
the preview gained learning-goal text. Exact whole-element title matching no longer matched the list
item's title-plus-goal. The regression now locates the lesson list item by title and additionally asserts
the specific goal. Explicit activation, no automatic start and correct-topic session checks remain.
The five targeted Home journeys pass against the final preview markup.

## 2026-10-03 — bounded lesson readiness requests

Skills reads now propagate query cancellation and abort after 15 seconds, with automatic retries disabled. A stalled read reaches the existing lesson-selection error and explicit Retry action rather than leaving Start disabled indefinitely. Errors remain distinct from empty topics; stale results cannot enable Start. No lesson activation or model routing changes.

Validation: 14 focused skills/Home tests, five isolated Home browser journeys (topic switching, activation-to-start, narrow widths), production build and targeted ESLint passed. Independent code and pedagogy reviews found no blockers. A live stale Home client recovered after reload; switching to an active topic enabled Start. The exact original loading cause was not established.
