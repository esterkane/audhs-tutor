# Five-destination shell: route and state contract

Design authority: Complete Design System PDF, page 6; see
[alignment](COMPLETE-DESIGN-ALIGNMENT.md). Inspected 2026-10-11.

## Concrete problem

The current shell groups Review, Vocabulary and Work alongside under Learn,
puts learning areas and the skill map under Explore, and offers no dedicated
Practice or Progress destination. Renaming these groups would leave the learner
with the wrong activity and would not implement the supplied design.

This is a navigation architecture gap, documented before changing application
code. This document is an implementation contract, not a completion claim.

## Destination map

| Primary destination | Intended entry and existing behavior to reuse | Required work |
| --- | --- | --- |
| Home `/` | Existing orientation, selection and sole saved-session ResumeCard | Preserve Continue and explicit topic-switch confirmation |
| Learn `/learn` | Resolve server current session using `useCurrentSession`; use `routeForPhase` for active learning | Add a read-only entry resolver. No current session returns to Home selection; read failure offers Retry, never a new session. Do not trust persisted session ID alone. |
| Practice `/practice` | Existing Review, Playground and Vocabulary activities | Add a small activity landing page with explicit descriptions. Navigation must not start an assessed block or record evidence. Review retains its own admission/session rules. |
| Progress `/progress` | Existing skill-map evidence and memory data | Add an evidence-oriented view after inspecting the API contract. Show assessed evidence and due review separately. Do not equate bookmarks, exposure or project completion with demonstrated understanding. Do not relabel the current map as a complete progress dashboard. |
| Explore `/areas` | Existing cross-course areas | Retain area browsing and links to Project study, Skill map, Search material and Sources without changing the learning goal on navigation. |

Active Learn state includes `/session` and `/recap`; `/review` is context-dependent
because it supports both session review and standalone practice. Determine its
parent from authoritative session state, not a hard-coded pathname alone.
Use one visible current destination and retain the specific page title.

## Destinations that must remain reachable

Tools contains Materials, Models, Experiments, Lesson drafts, Saved answers,
Playground, Audio visualizer, Vocabulary and Work alongside. Preferences remains
in the navigation footer. Preserve Project study, Search material, Sources,
Skill map and Correction drafts through appropriate Explore/content links and
quick navigation. Keep current URLs and deep links working; no data migration.

## Session invariants

- `features/session/api.ts:routeForPhase` remains the phase-routing authority.
- Opening navigation cannot POST start/end/advance/prepare or award evidence.
- Home Continue retains explicit resume preparation; Learn routing itself must
  not create another ResumeCard or prepare a model merely by rendering a link.
- Leaving a page preserves existing server checkpoint and local draft behavior.
- Refresh, Back/Forward and late current-session responses must not override a
  more recent navigation intent.
- Loading and unavailable-server states have visible feedback and recovery.

## Implementation sequence and likely files

1. Add/test the read-only Learn entry (`routes/Learn.tsx`, `app/App.tsx`, route
   tests). Reuse existing query and phase routing; no backend/kernel changes.
2. Add Practice and Progress landing views from verified existing contracts;
   keep unimplemented evidence visibly unavailable rather than inventing it.
3. Replace shell grouping with all five destinations together, retaining Tools
   and Preferences. Likely files: `app/App.tsx`, `index.css`, existing shell
   tests and browser navigation journeys. Use shared semantic tokens.
4. Verify 240px desktop navigation, 48px rail, five mobile destinations and Tools
   sheet against the PDF. Then consolidate the header and lesson ContextBar in
   separate bounded slices; do not fold unrelated screen redesign into routing.

## Acceptance gates

Read-only navigation tests must assert zero lifecycle/model writes. Exercise
current teach/review/recap, completed and absent session, stale local ID, API
failure and slow response followed by navigation away. Verify Home's single
resume action and explicit switch behavior remain unchanged.

For the shell, run desktop/narrow, keyboard, Back/Forward, refresh, light/dark,
large text and reduced-motion journeys. Check every retained destination,
focus after route changes, Tools Escape/return focus and no overlapping mobile
targets. Visually inspect rendered output; compilation alone cannot close this.

Owner comprehension, real browser zoom and assistive-technology acceptance
remain open. No new library, model/provider, grading or learning policy is
needed for the route migration.

## Baseline verified

`pnpm exec playwright test e2e/home-session-intent.spec.ts`: 2 passed at
390px and 1280px against the isolated sandbox. Existing Home keeps the saved
lesson visible, does not write on selection/confirmation display, and ends and
starts a session only after explicit confirmation. Optional resume preparation
failure does not block navigation. This is a baseline, not evidence for the
unimplemented shell. Application code and learning logic are unchanged.

## Learn entry implemented

`/learn` now refreshes the server current-session query before routing through
`routeForPhase`. It ignores stale persisted identity, returns an empty session
to Home selection, and offers Retry/Home after failure. The shared bounded read
cancels on leaving and times out stalled transport/body reads after15s. No
session lifecycle, model preparation or learning-policy writes were added.
The shell links remain unchanged pending the complete destination migration.

Verification:12 targeted Learn/App unit tests, targeted ESLint and production
build pass. Five browser journeys passed: Home regression at390/1280px, Learn
keyboard/error recovery at320/1280px, and real sandbox session routing/reload
with unchanged checkpoint and no POST requests. Narrow recovery screenshot
visually inspected; desktop recovery covered by browser assertions. Review
identified unbounded reads; fixed with existing boundedRead and timeout/body/
cancellation regression tests. Remaining: full shell, Practice/Progress, dark/
large-text shell acceptance and human comprehension.

## Practice entry implemented

`/practice` now offers lesson/session practice, coding experiments, language
activities and project study through existing routes. It explains admission
without starting sessions or writing completion. Current review requires a
session, so the lesson entry resolves via `/learn`, not a dead standalone
`/review` link. This is the navigation entry, not completion of page10's
exercise/feedback blueprint. Shell destination exposure remains pending.

Two isolated browser journeys passed at320/1280px: explicit link targets,
44px controls, keyboard activation, focus after navigation, Back and zero API
writes on entry. Narrow screenshot visually inspected; targeted ESLint and
production build passed. Bounded code/copy review found no actionable issues.

## Progress API gap and next slice

PDF page10 requires Understanding, Practice and Independent application rows
with level/date and an expandable explanation of underlying evidence. The
current `/api/skills/map` returns dimension score/count/confidence and memory
counts, without evidence dates or records. Do not use that payload alone as
the completed Progress view.

Existing `CompetencyEvidence` stores dimension, score, weight, grader level,
source attempt and timestamp; `CompetencyState` stores last_evidence_ts. The
next bounded vertical slice should expose learner-scoped, read-only evidence
with source attempt details and dates through typed API schemas, then render
the three design rows and a separate recall/memory summary. Preserve existing
competency aggregation; do not infer independent work from transfer evidence
without inspecting whether the attempt records help/solution exposure.

Before implementing display levels, inspect the assessment rubric and evidence
provenance. No evidence must read as not yet checked, not failure. Distinguish
model judgement, observed attempts and self-report; show unavailable provenance
explicitly. Verify learner isolation, absent/partial evidence, stale/loading/error
states, chronology and no mutation. Generated client types must come from the
OpenAPI schema. The skill map stays a secondary view; no new progress scores,
thresholds or invented dates.

### Progress evidence API implementation in progress

A typed, read-only `/api/skills/{skill_id}/evidence` endpoint now exposes dated
records with dimension, recorded score/weight, grader source and the linked
attempt's reported hint count. It is learner-scoped, paginated (maximum100),
ordered by timestamp/ID, and does not refresh/write competency. Missing or
cross-learner attempt provenance stays null. Independent work is explicitly
`not_verified`: hint_count is client-reported and does not cover all exposure.

Three focused backend tests pass, covering dates, pagination, missing skill,
input bounds, learner isolation including corrupt cross-learner attempt links,
no competency-state creation and no independence claim from zero hints. Ruff
passes; OpenAPI/client types regenerated. This is unfinished local work: UI,
full type checking, review and publication remain. Do not treat the raw score
as a UI mastery percentage or these records as a complete explanation of the
original question/rubric; detailed immutable attempt provenance still needs
inspection before the explanation panel can claim it.

### Progress evidence view verified — 2026-10-11

`/progress` now offers concept selection, dated Understanding/Practice/Recall
evidence and explicitly unverified Independent application. Paginated records
show grading provenance and reported hints; no mastery percentage or independent
work inference. Counts/latest dates aggregate the full evidence set, not just
the visible page. Selecting a lesson uses the existing Home confirmation flow.

Three backend checks, Ruff, full backend mypy (221 files), frontend ESLint and
production build pass. Two320/1280 browser journeys cover keyboard disclosure/
pagination, page-failure retention/retry, empty evidence, concept switching,
Back, no horizontal overflow and no POST requests. Narrow rendered page
visually inspected. Review caught pagination-error loss of loaded records;
retained-page recovery implemented and re-reviewed. An initial browser run
exposed an ambiguous concept label; explicit label/id now verified. One
overlapping rerun was rejected by the sandbox's occupied-port guard; the final
isolated run passed.

Limitations: rubric/question snapshots and meaningful proficiency levels are
not yet surfaced; no independent-work verification exists. Current design
rows honestly report evidence availability instead of inventing levels. The
next-useful-evidence link reuses the learning session rather than introducing
a separate recommendation engine. Full PDF page10 and human comprehension
acceptance remain open. Shell destination exposure is next.

## Five-destination navigation implemented — 2026-10-11

Primary navigation is Home/Learn/Practice/Progress/Explore. Desktop uses the
240px sidebar with a48px collapsed rail; below768px it becomes a persistent
five-item bottom bar. Tools opens a native modal sheet/dialog; Preferences
remains in the footer. All former routes remain in Tools or primary navigation
and quick search. Source search/map and active session routes keep explicit
parent navigation, while page titles preserve their actual identity.

No session or preference mutations were introduced. Native dialog Escape
restores the Tools trigger; choosing a page closes the dialog and focuses main.
A reviewed resize regression was fixed: when the rail toggle is hidden at a
breakpoint, focus moves to a visible primary link. Lesson/model/assessment
logic remains unchanged. Existing menu journeys were updated to the new
visible primary links and Tools surface without dropping their recovery tests.

Initial verification:601 frontend unit tests, targeted ESLint and production
build; three shell journeys at320/390/1280 including keyboard, Back/Forward,
rail resize,200% text overflow and axe;24 affected journeys covering source
search, map recovery, Preferences and saved thoughts. Narrow shell screenshot
visually inspected. Additional Tools resize/navigation verification is tracked
in the final slice handoff. Code review focus finding addressed and confirmed.

Not full PDF completion: compact48px global header, Learn ContextBar/Focus,
context-panel breakpoints, cross-theme shell checks and human/screen-reader
acceptance remain. The current change delivers navigation taxonomy and
responsive destinations without redesigning unrelated screens.

Final Tools resize/route journey passed. Project-study fixture is empty to isolate shell history from automatic project-selection query changes. Total affected browser checks:28.

Next layout phase: [header/context ownership contract](HEADER-CONTEXT-CONTRACT.md). Keep audio, capture and session lifecycle ownership intact when compacting the shell.
