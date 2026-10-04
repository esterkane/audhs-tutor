# Product understanding — Phase 1

Date: 2026-10-04. Scope: current AuDHS Tutor repository, before design changes.

## Evidence and limits

This is a **source-grounded product inventory**, not a usability verdict. It follows the Phase 1 requirements in the supplied UX/design plan. The route map, component behavior and architecture statements below come from inspected implementation and documentation. The journey steps describe supported paths inferred from source. Confusion points are **hypotheses for observation**, not reports of user behavior.

No manual browser scenario, accessibility certification, learning-effectiveness study or timing measurement is claimed by this document. Runtime audit observations belong in the separate UX audit report, with their own environment and evidence. Existing tests demonstrate selected contracts, not comprehensibility. The repository contains more features than were exhaustively exercised in this source pass; later phases must validate these journeys rather than treating this inventory as a completed evaluation.

Primary sources: [README](../../README.md), [architecture](../ARCHITECTURE.md), [shell and routes](../../frontend/src/app/App.tsx), [Home](../../frontend/src/routes/Home.tsx), [Session](../../frontend/src/routes/Session.tsx), [Review](../../frontend/src/routes/Review.tsx), [database models](../../backend/app/db/models.py), [planner](../../backend/app/kernel/planner.py), [adaptation](../../backend/app/kernel/adaptation.py), and the feature sources linked below. Architecture documentation is historical context; current code takes precedence where they differ.

## Product purpose

AuDHS Tutor is a personal, local-first learning workspace. It connects selected goals and course material with explanations, practice, feedback, delayed review and a place to resume. The intended audience includes adults with variable attention or capacity, including AuDHD learners; it does not assign a diagnosis or a fixed learning style.

The organizing problem is broader than answering a question: deciding what to work on, understanding difficult material, practicing it, retaining useful context across interruptions, and distinguishing activity from demonstrated understanding. Learners can choose an area spanning courses, pursue a project, review prior learning or experiment with code.

Unlike a generic chatbot, the app maintains a skill graph, explicit sessions and checkpoints, source provenance, assessment evidence and spaced-review scheduling. A deterministic learning kernel owns learning state; models produce explanations and grading proposals through bounded interfaces. The learner chooses whether to accept adaptations. Generated content and grades are not presented in the README as unquestionable truth or proven learning efficacy.

The intended loop is: **choose a goal → explore material → explain and practice → inspect feedback → stop safely → return → apply the idea elsewhere**. Imported material is searchable before a draft is activated. Activation makes lesson skills available locally; it is not public web publication. Project-study notebook calculation checks are a separate achievement from grading an explanation or completing a course.

## Current information architecture

```text
Application shell
├─ Persistent: brand/Home, audio controls, mode + energy
├─ Session present: Resume or manage session → Home
├─ Primary navigation
│  ├─ /                    Home: resume/start, goal, session options
│  ├─ /areas               Learning areas: cross-course topics and draft review
│  ├─ /programs            Project study: programme, tasks, notebook workspaces
│  ├─ /playground          Playground: independent code practice and tutor help
│  └─ /playground/visualizer Audio visualizer
├─ More tools (disclosure)
│  ├─ /answers             Saved answers
│  ├─ /answers/:answerId   Individual saved answer
│  ├─ /map                 Skill map / skill state
│  ├─ /together            Together
│  ├─ /experiments         Personal learning experiments
│  ├─ /vocab               Vocabulary
│  ├─ /corpus              Materials: import, inspect, retrieval tools
│  ├─ /curriculum          Lesson drafts: review, edit, activate
│  ├─ /models              Model readiness, downloads and routing
│  └─ /preferences         Preferences, adaptation history and undo
├─ Workflow routes (not standalone main-navigation entries)
│  ├─ /session             Explanation / assessment / challenge / practice
│  ├─ /review              Recall and explicit self-rating
│  └─ /recap               Finish session and inspect recap
├─ Persistent auxiliary components: LearningCompanion, tangent parking button
└─ Unknown route: Page not found + Return Home
```

The shell sets document titles, provides a skip link and focuses the main region on pathname changes. Default content width is `max-w-3xl`; programme/playground routes use `max-w-7xl`. Main navigation and cards use wrapping layouts. These are implementation choices, not proof of narrow-screen usability.

### Major components and settings

- Session composes explanation controls, streamed tutor output, sources, representations, question help, assessments, voice and block controls. Optional controls use disclosures.
- Review composes a frozen card, optional confidence, reveal, explicit rating, recovery information and block/session controls.
- Areas and Curriculum share draft editing; sources and draft coverage are distinct from activated lessons. [Areas](../../frontend/src/routes/Areas.tsx), [Curriculum](../../frontend/src/routes/Curriculum.tsx)
- Project study composes task work, notebooks and a study tutor. Notebook edits persist in browser storage; computation runs in a fresh browser Python sandbox. [NotebookWorkspace](../../frontend/src/features/programs/NotebookWorkspace.tsx)
- Preferences expose registered settings; Models is a separate operational screen. Sensory preferences include theme, density, text scale and reduced motion. [preference registry](../../backend/app/kernel/preferences.py), [sensory application](../../frontend/src/features/sensory/useSensory.ts)

### Visible and less-visible state

| State | Visible representation | Storage / boundary not necessarily apparent from the screen |
| --- | --- | --- |
| Mode and energy | Global header and Home options | Browser-persisted selection; session has its own recorded values |
| Selected goal | Home area/course controls and topic labels | Area goal takes precedence over course goal; selected scope feeds planning |
| Session progress | Home resume, current block, next/stop actions, recap | Backend session checkpoint owns block ID, phase and running/ended state |
| Work in progress | Answer text, notebook edits, explanation output | Lifetimes differ: component memory, tab-local recovery, browser-local notebook storage |
| Submitted answer | Feedback, recovery panel, saved-answer status | Request identity, staged grade, learning commit and history save are distinct states |
| Review | Due counts, revealed answer, Again/Hard/Good/Easy | FSRS scheduling is separate from skill competency evidence |
| Skill progress | Skill map, mastery and assessment feedback | Evidence dimensions, confidence, decay and prerequisites influence derived state |
| Adaptation | Suggestion with reason; log and undo | Deterministic detectors observe events; accepted preferences have origin/trial lifetime |
| Materials | Import outcomes, documents, sources | Provenance, trust, versioning, quarantine and retrieval filters are not the same as course completion |
| Notebook checks | Check results and return-results action | A passed code snapshot does not grade the learner's explanation; code changes invalidate it |

Sources: [mode store](../../frontend/src/stores/mode.ts), [block state](../../backend/app/kernel/blocks.py), [memory](../../backend/app/kernel/memory.py), [competency](../../backend/app/kernel/competency.py), [assessment recovery](../../frontend/src/features/assess/useAssessmentSubmission.ts), [model definitions](../../backend/app/db/models.py).

## Core learner journeys

All fifteen rows are source-derived journey definitions. “Possible confusion” is an audit hypothesis. Setup/model availability is a prerequisite to test, not an assumption that every launch succeeds.

| Journey | Starting state and intent | Steps required | Information needed | Possible confusion to validate | Completion state | Recovery path |
| --- | --- | --- | --- | --- | --- | --- |
| 1. First launch | No active session; find a useful starting point | Open Home; inspect next step; choose/default topic; start | Whether lessons/material and required services are ready | Empty topics versus missing setup; main navigation offers several starting concepts | Session or selected preparation path opens | Home shows selection/loading failures; use retry, area preparation or Models as applicable |
| 2. Choose/start topic | Home or Areas; learn something specific | Choose area or course; inspect available lesson; activate reviewed draft if needed; start | Area/course scope and distinction between draft and active lesson | Materials, areas and course lessons may appear interchangeable | Session starts within chosen available scope | Empty selection remains explicit; inspect sources/draft or choose another topic |
| 3. Continue topic | Existing backend session and browser context; continue | Home → resume/manage → current workflow route | Current topic, block and saved state | Browser selection may be mistaken for authoritative session state | Correct activity and available retained work reopen | Retry session load; retain existing work if background refresh fails |
| 4. Receive explanation | Teach phase, ready route; understand one idea | Start explanation; read output and sources; try a question when ready | What is being explained and whether generation is running/finished | Stream completion, save status and learning progress may be conflated | Explanation available; learner chooses next action | Stop stream; inspect response/save status; explicitly retry appropriate operation |
| 5. Ask follow-up | Explanation or project context; clarify a point | Enter follow-up in contextual tutor; send; inspect reply | Which topic/work the tutor is using | Several tutor surfaces may suggest shared conversation context | Reply shown in that surface; saved status separate | Interrupted response recovery; retain typed work and inspect saved answers |
| 6. Say “I don't understand” | Stuck on explanation/question | Use stuck/hint action or question-help explanation | Whether action supplies a hint versus a solution | Exact phrase is not a universal control; actions differ by surface | Smaller hint/concept explanation appears | Keep original task; ask another question or stop/change topic |
| 7. Different explanation | Existing explanation; try another representation | Open explanation/representation controls; request alternative; compare | Original objective and source continuity | Representation preference may be mistaken for evidence of learning | Alternate content available without automatically proving mastery | Keep original/current text; inspect sources and generation errors |
| 8. Incorrect answer | Assessment shown; learn from a mistake | Optional confidence; answer; submit; read criteria/next step; use help or retry deliberately | Correctness, evidence, hints and what counts as a new attempt | Retry grading versus save-only recovery; confidence versus correctness | Feedback and recorded evidence, or explicit failure state | Preserve answer/identity; check result before resubmitting; refresh changed content explicitly |
| 9. Review learning | Due cards and session; recall | Open Review; recall; optionally state confidence; reveal; rate; advance | Rating meanings and help-used constraints | Self-rating is not an automatic objective correctness score | Review schedule updated once; queue advances | Check saved rating; same-identity resend only when supported; refresh stale card and reveal again |
| 10. Stop mid-session | Running learning block; leave safely | Use stop/save or session controls; await acknowledgement; recap as appropriate | Whether block stopping and whole-session finishing are separate | “Stop”, pause, and “Finish session” may imply identical persistence | Block/session state confirmed, or learner remains with error | Retry authoritative state/end operation; no forced answer required |
| 11. Return later | Prior session, drafts or saved answers; regain context | Open Home; resume; inspect saved content/recovery if present | What survives navigation, refresh and a new browser tab | A browser-local draft is not necessarily a server save | Context restored to documented storage boundary | Saved answers/server checkpoint; explicit retained-answer recovery; storage warnings |
| 12. Understand progress | Some learning evidence; decide next work | Inspect Skill map, feedback/review and recap | Difference between recall schedule, competence and activity count | Multiple progress representations may not explain their relationship | Learner can identify evidence and a next step | Inspect criteria/sources; avoid treating sparse data as certainty |
| 13. Change preferences | Home/options or Preferences; adjust experience | Change explicit setting; inspect adaptation proposals; accept/decline or undo | Scope, duration and reversibility of change | Raw preference keys and tooltip-only trial details may be unclear | Preference stored or explicit failure shown; accepted adaptation logged | Retry failed write; undo accepted setting; trial expires at next session |
| 14. Change modality | Text explanation/task; prefer speech, representation or code | Choose available representation/read-aloud/voice; for voice connect then talk or type | Model readiness, microphone permission and what is recorded | Listening to existing text differs from generating a voice conversation | Chosen modality active with text context retained as supported | Interrupt audio, close voice, type fallback; inspect Voice setup/readiness |
| 15. Recover from errors | API/model/storage/runtime failure; retain work | Read failure; choose load retry, result lookup, finish saving, content refresh or runtime restart according to state | Whether inference/evidence already happened | Generic “retry” cannot safely mean the same thing for every failure | Original operation confirmed or a safe unresolved state retained | Preserve request ID/draft; do not auto-regrade; explicit page-memory fallback warns about persistence limits |

Journey implementation sources: [Home](../../frontend/src/routes/Home.tsx), [Session](../../frontend/src/routes/Session.tsx), [QuestionHelp](../../frontend/src/features/assess/QuestionHelp.tsx), [Review](../../frontend/src/routes/Review.tsx), [Recap](../../frontend/src/routes/Recap.tsx), [Map](../../frontend/src/routes/Map.tsx), [AdaptationCards](../../frontend/src/features/adaptations/AdaptationCards.tsx), [VoicePanel](../../frontend/src/features/voice/VoicePanel.tsx), [AssessmentRecovery](../../frontend/src/features/assess/AssessmentRecovery.tsx).

## Existing design system

The inspected system has a deliberate semantic foundation, with many route-specific compositions. It is neither absent nor a complete documented component system. A redesign should reuse its tokens and primitives before introducing replacements.

| Element | Current source-grounded implementation | Audit question, not a finding |
| --- | --- | --- |
| Colors | Semantic `bg`, `fg`, `muted`, `card`, `line`, `accent`, `accent-fg`, `ok`, `warn`; light/dark variants | Are warning/error roles and contrast consistent in rendered contexts? |
| Typography | System sans; body line-height 1.55; prose 1.75 and 68ch; prose headings scale by em; route headings use Tailwind sizes | Does each page have a clear semantic and visual heading hierarchy? |
| Spacing | Tailwind utility scale, commonly p-4/gap-2/gap-4; compact setting overrides all nested main grids to 0.5rem gap | Does compact mode change complex workspaces unexpectedly? |
| Radius/shadow | Buttons rounded-md; cards rounded-lg with shadow-sm; prose code has 3px radius | Are containers distinguishable without visual clutter? |
| Buttons | Primary, secondary, ghost, outline; sm/md/lg; default secondary; disabled/hover/pressed support | Is one clear primary action discernible in each learning state? |
| Forms | Shared Textarea and Choice; native inputs/selects and route-local styling remain common | Are labels, errors, keyboard use and touch targets consistent? |
| Cards | Shared visual Card; CardTitle renders h2 | Are nested cards or pages starting at h2 understandable to assistive navigation? |
| Dialogs | Tangent parking uses Radix Dialog with title/description, overlay and close controls | Does focus return correctly and is Escape predictable? |
| Navigation | Text links, active accent styling, More tools disclosure, skip link/main focus | Can learners locate sessions and distinguish the learning entry points? |
| Icons | Audited primitives and shell rely on text; no shared icon primitive established by this pass | Inventory feature-specific icons before setting global icon rules |
| Status | Inline role=status/alert, disabled controls, progress text and feature recovery panels | Are saving, saved, grading, staged and recorded states distinguishable? |
| Motion | OS reduced-motion CSS plus preference-applied restraint; sound/ambient opt-in preferences | Verify actual animation/audio behavior and preference changes in browser |

Sources: [global styles](../../frontend/src/index.css), [Button](../../frontend/src/components/ui/button.tsx), [Card](../../frontend/src/components/ui/card.tsx), [Choice](../../frontend/src/components/ui/choice.tsx), [Textarea](../../frontend/src/components/ui/textarea.tsx), [parking dialog](../../frontend/src/components/ParkingLotButton.tsx), [sensory settings](../../frontend/src/features/sensory/useSensory.ts).

## Architectural safeguards to preserve

1. **Kernel state ownership.** Keep block checkpoints, competency evidence and FSRS scheduling authoritative; reducing visible controls must not alter learning policy. Memory scheduling and competence remain separate.
2. **Explicit adaptation.** Proposed changes have reasons and learner decisions; defaults/trials are reversible. UI simplification must not silently apply suggestions or erase the adaptation log.
3. **Source and content boundaries.** Retrieved material is untrusted data; provenance/trust/versioning matter. Draft activation remains explicit. Presentation changes must not turn sample coverage into claims of complete course coverage.
4. **Submission identity and exact content.** A lookup is not a new grade. Version-bound assessments/reviews prevent applying work to changed questions. Completed results replay; uncertain work remains recoverable without duplicate evidence.
5. **Staged grade versus learning commit.** Saved grading output can be inspected and explicitly finished without another inference. Feedback visibility is not itself proof that progress was recorded. [assessment requests](../../backend/app/orchestrator/assessment_requests.py)
6. **Bounded asynchronous work.** Session/review loads have deadlines; cached content remains mounted on refresh failure. Obsolete results must not overwrite a different session/activity. [boundedRead](../../frontend/src/lib/boundedRead.ts)
7. **Execution boundaries.** Notebook/Python work stays in browser runtime; calculation checks refer to a particular code snapshot. Pausing stops active work without discarding already completed snapshots; code changes invalidate those results.
8. **Local-first routing and privacy.** Hosted inference is optional with server-side credentials and budget accounting. Voice activation, playback and retention need visible consent/control; restored text must not silently restart recording or playback.

Existing contract examples worth retaining during subsequent design work: [Session tests](../../frontend/src/routes/Session.test.tsx), [Review tests](../../frontend/src/routes/Review.test.tsx), [assessment recovery tests](../../frontend/src/features/assess/useAssessmentSubmission.test.tsx), [notebook tests](../../frontend/src/features/programs/NotebookWorkspace.test.tsx), [assessment finish recovery](../../backend/tests/test_assessment_finish_recovery.py). These references are not a claim that this documentation task reran them.

## Questions for the runtime audit

- Can a first-time learner explain the difference between Materials, Lesson drafts, Learning areas and Project study after a short visit?
- Does returning after interruption expose one clear next step and an honest statement of what was retained?
- Can the learner distinguish a saved explanation, saved grade, applied learning result, notebook check and course completion?
- Do error panels preserve orientation without making recovery terminology the main learning task?
- Are preferences and alternate modalities discoverable without becoming prerequisites to begin?
- Do keyboard, narrow viewport, enlarged text and reduced-motion operation preserve all essential actions?

Do not answer these questions from code alone. Record observations, prerequisites, screenshots and limitations in the audit before proposing or implementing design changes.
