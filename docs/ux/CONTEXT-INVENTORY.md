# C0 route and context inventory

2026-10-04. Read-only runtime/code investigation before C1 shell changes. No application code changed. Replaces the old proposed route grouping, not the existing routes or learning kernel.

## Concrete problem

The shell presents five primary links plus nine mixed More tools destinations. Source administration, practice, configuration and saved work compete without a clear hierarchy. Existing route focus and current-page title must survive regrouping. Audio is already collapsed by default; do not redesign it on the premise that it is always expanded.

## Route destination contract

| Existing route | C1 group / entry | Context to preserve |
|---|---|---|
| / | Home | Current server session and independent new-session choices |
| /?lesson=ID | Home selected-lesson intent | Keep current or explicitly End and start; preserve query and eligibility preflight |
| /session | Learn / Current activity | Server phase, session, skill, block and pending request identities |
| /review | Learn / Review | Server review evidence and tab-scoped queue; no rating from navigation |
| /recap | Learn / Session recap | Existing completion actions; unsaved fields are currently route-local |
| /together | Learn / Work alongside | Same current session; explicit ambient sound; retain direct route |
| /areas | Explore / Knowledge areas | Preserve area/draft query links; local selector state is not a global area context |
| /map | Explore / Skill map | All nodes, locks, prerequisites and explicit selected-lesson navigation |
| /programs | Projects | Browser-saved course/section/notebook place; notes and checked outputs |
| /answers | Library / Saved explanations | All existing query filters, cursor and search |
| /answers/:answerId | Library / Saved explanation | Exact answer ID, provenance and Back to saved answers filters |
| /playground | Tools / Coding playground | Per-activity draft/code/chat; standalone usage remains |
| /playground/visualizer | Tools / Audio lab | Existing views/presets; playback lifecycle not expanded into persistent cross-route playback |
| /vocab | Learn / Vocabulary and listening | Existing decks/listening; reachable regardless of chosen area |
| /corpus | Manage / Sources | Imports, stop/resume/status, trust/retrieval controls remain |
| /curriculum | Manage / Lesson drafts | Explicit editing/save/activation; no publish from opening navigation |
| /models | Manage / AI and voice | Local services, readiness, routing and budgets |
| /experiments | Manage / Learning experiments | Existing lifecycle/assignments; no enrollment on navigation |
| /preferences | Manage / Preferences | Saved values and adaptation semantics; contextual links retained |
| unmatched | Not found | Clear existing Home recovery |

C1 grouping is navigation, not new landing pages. Library initially names the existing saved explanation capability; no invented Notes/Collections feature. Reading source citations remains contextual; source administration lives in Manage. Together retains a discoverable link until C3 tests its mode presentation. Review remains available independently of area classification.

## State ownership and return contracts

- Server session is authoritative. `features/session/api.ts:routeForPhase` routes running review to /review, completed/recap to /recap, otherwise /session. `useMode` persisted IDs are hints, not proof an active session exists. A new Learn entry must check current state and handle read failure, not blindly navigate by persisted ID. It may expose Home's existing resume/start flow before a dedicated resolver is justified.
- Home `goal.area`/`goal.course` preferences select new work. `SelectedLesson` keeps current target until explicit End and start, checks eligibility first, and separately reports an ended previous session when new start fails. Shell browsing must not call this mutation.
- Lesson unsent text and stream cache use tab storage scoped by session ID, block index, block start time and skill ID. Do not promise cross-device or post-tab-close retention. Pause is navigation and does not end a session.
- Review queue uses session-scoped sessionStorage; authoritative ratings stay server-owned. Reopening must not generate ratings.
- Projects stores versioned course/section/notebook location in localStorage. GuidedSection stores work separately; NotebookWorkspace identity includes baseline content hash and invalidates incompatible source edits. Return checked output is explicit and does not mean project completion.
- StudyTutor persistence is scoped by session and explicit identity or context. Shell LearningCompanion captures selection/page text only when opened; it is keyed by pathname, and inner tutor is keyed by captured passage. A persistent sidebar needs context/unsent request handling before removing either key.
- Answers list uses URL query filters; detail has exact answer identity and Back to filtered list. SourceViewer stays a contextual dialog and returns focus to citation.
- Playground restores per-activity code/prediction/chat but selected activity initializes to Scratch. Run result and unsent question are route-local. Recent work links must encode/restore the activity before claiming a full return.
- Areas reads area/draft URL only as initial selection; select changes do not update the URL. Curriculum course/selection and unsaved editor text are component state. Do not promise universal route return protection for either.
- Recap notes, energy and recall selection are component state before submission. Global navigation can lose them today. Record as a recovery gap; do not disguise this with new navigation wording.
- Visualizer file, source and playback position are component state; named local preset storage is separate. Navigation is not the same continuity contract as its internal Watch/Learn/Create tabs. No automatic audio resumption.

## Current-run evidence

23 browser journeys passed against fresh disposable services, no live learner database or hosted inference:

- home-resume.spec.ts (4): named saved topic, keyboard authoritative review resume at390/800/1280; empty topic preparation link.
- home-area-readiness.spec.ts (5): ready→empty→ready, explicit selected-topic start;320/390 reflow; preparation→activation→Home at390/1280. Synthetic content/activation routes are fixtures, not actual owner publication.
- session-pause.spec.ts (9): teach/assess/review pause and refresh at390/1280 preserve exact server checkpoint; teaching draft retained; no writes from Pause; late responses cannot undo pause. Disposable session creation/cleanup is test setup.
- task-notebook.spec.ts (1): real local notebook execution/check, retained notes and checked return after pause/refresh; tutor feedback is synthetic.
- representation-sources.spec.ts (2): keyboard source inspection, missing-source feedback, dialog close focus and historical provenance at desktop/narrow. Tutor output is synthetic.
- saved-answers.spec.ts (2): filtered saved-answer keyboard round trip and history without generation/session POSTs atdesktop/390.

Seven unit tests passed in SelectedLesson.test.tsx and lessonStorage.test.ts: selection/preflight/keep-current behavior and scoped draft/storage failure behavior. Existing screenshots from pause journeys are generated in test-results; no new full visual acceptance claim. Existing map-recovery evidence shows the narrow Park overlap. No application edit, so build/lint rerun is not needed for this documentation slice.

## C1 implementation boundary

Likely files: frontend/src/app/App.tsx (or a small navigation component extracted from it), existing shell tests and focused navigation browser journeys. Reuse semantic tokens and native disclosure/link patterns; no library. Keep Router, QueryClient, Shell children, page focus, audio owner and Companion lifetime stable. Do not replace full route content or change storage keys. Check all destinations, active group, keyboard,320/390/1280 and200% text, Back/Forward, no learning writes, existing session/draft tests. Test error/no-session/current-session states before adding a direct Learn resolver.

Compare current visible choices to grouped choices using the same locate-saved-answer, manage-models, resume and tool-detour tasks. Fewer top-level links alone is not proof of improved usability. Owner comprehension, real delayed return and physical audio remain open. Existing state gaps are separate follow-ups; C1 must not worsen or silently claim to solve them.
