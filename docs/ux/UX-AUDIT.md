# UX audit — Phase 2

2026-10-04. Baseline: pause/end clarification already shipped. This is the next phase of the supplied UX/design plan, not a redesign or a claim of accessibility certification. Application code and learning logic were not modified in this phase.

## Method and evidence

- Inspected all 17 route entry states at **390, 800, 1280 and 1920 CSS pixels**, height 900, using Chromium and the existing seeded sandbox. The explicit programme fixture was empty to exclude private material from captured evidence. Session/review/recap inventory captures their no-session states; active flows are evaluated separately below.
- Manually exercised Home → session → optional movement → review → explanation → practice, Areas discovery, project Understand → Try, local code execution, visualizer still-mode demo, model readiness, material-path errors and secondary-tool entries on a separate disposable database.
- Ran nine opt-in audit probes (four viewport inventories, five backend-failure probes), 16 existing browser journeys, seven voice-panel unit tests and ESLint. All probes completed; **a completed audit probe is not a clean accessibility result**. Findings are recorded below and in JSON.
- Reused the previous [adversarial report](ADVERSARIAL-USABILITY-REPORT.md) for refresh, keyboard, pause/resume and transition-race evidence. Earlier findings remain open unless explicitly corrected.
- Read-only architecture/semantics review supported runtime investigation. Source hypotheses are not promoted to observed failures.

Reproduce the inventory from `frontend`:

```sh
AUDHS_UX_AUDIT=1 pnpm exec playwright test e2e/ux-audit.spec.ts --reporter=list
```

This test is skipped in ordinary CI. It collects findings instead of asserting that the application has none. Each route is sampled after 500ms plus axe execution; this is not proof that all background work has settled. Failure probes keep all API calls at HTTP503 for nine seconds, covering the default query retry window. They verify Home remains reachable; they do not assert incorrect loading text as desired behavior.

Evidence: [390px](evidence/phase2/inventory-390.json), [800px](evidence/phase2/inventory-800.json), [1280px](evidence/phase2/inventory-1280.json), [1920px](evidence/phase2/inventory-1920.json). These retain headings, dimensions and axe findings, excluding source text. Screenshots inspected: [Models/mobile](evidence/phase2/models-390.png), [Home/tablet](evidence/phase2/home-800.png), [Playground/laptop](evidence/phase2/playground-1280.png), [Preferences/desktop](evidence/phase2/preferences-1920.png).

## Executive assessment

The application has useful recovery mechanisms and clearer task guidance than its broad navigation suggests. The strongest remaining problems concern **honesty of state and outcomes**, not colors or decorative polish: failed reads resemble empty/loading states, detailed tutor output can be labelled complete despite omissions, and displayed mastery can rise after incorrect answers. The last issue crosses into the learning model and must be reviewed explicitly before changing code.

Cognitive-load severity here uses the requested **low / medium / high** scale. It is separate from axe's technical impact and the later Phase 3 S0–S4 prioritization. A missing h1 warning is not automatically a WCAG violation; axe's “serious” label is not automatically a task-blocking S3 finding.

## Screen and flow inventory

| Screen / flow | Orientation and next action | Cognitive load / hierarchy | Predictability, agency and saved state | Evidence / severity |
|---|---|---|---|---|
| Home | Topic and primary Start/Resume visible; new-session controls distinguished from resume | A second goal panel repeats target information and requires understanding area/course precedence | Resume retains session; Start is distinct. Stale browser session ID can leave the shell's resume/manage link visible after a fresh database reset | Manual + four sizes; **medium**. Reset-only shell case is not ordinary data loss |
| Learning areas | Source-backed cross-course purpose is stated; discovery leads to an area selector | Sixteen suggested categories included many with zero course/source candidates in the small seed; choice list expands before there is useful content in each category | Source match is correctly disclaimed as not a prerequisite. Activation remains explicit | Manual discovery + inventory; **medium**, seed-scale observation only |
| Project study | Understand → Try → Think deeper, current step, pause and notebook entry are explicit | Focused idea/example before task; advanced files/sources collapsed | Task notes explicitly browser-local, not submitted project. Small task starter distinguished from full notebook | Manual read/task entry plus project-orientation desktop/320px tests; **low–medium**. Populated course screenshot excluded |
| Playground | Starter code and Run code are visible; actual local run printed expected greeting | Code/tutor split is useful on laptop; tutor panel explains session requirement but adds setup before chat | Code and chat local-save scope stated; output temporary. Tutor does not silently run code or award mastery | Manual run + slow/stop/retry/draft browser tests; **medium**. Invalid ARIA label noted below |
| Audio visualizer | Silent demo versus local file/play is explained; sound/motion status explicit | Many transport/preset choices remain, but advanced measures are collapsed | Reduced-motion demo changed a manual sample and reported running while picture stayed still; explicit Next sample exists | Manual Start demo + inventory; **medium**. No audio-perception claim |
| Saved answers | Reopening versus regenerating is clearly distinguished; search scope stated | Search/filter understandable; full conversation context excluded from search is disclosed | Keyboard round-trip tests preserve destination; no new model call when browsing | Existing saved-answers journeys + inventory; **low–medium** |
| Skill map | Text list explains locked/next/mastery alongside diagram | Repeated Learn this labels require row context; graphical density requires optional list | Text alternative exists. Failed API remains Loading map with no route-specific retry | Inventory, source, failure probe; **medium**, accessible button-list clarity still needs human test |
| Together | Explicitly a quiet focus screen, not a human companion; Home link if no session | Minimal content; duplicate global/local audio entry | No scoring implied. Absent/error session data distinction remains a source concern | Manual empty state + inventory; **low**, failure distinction unverified here |
| Experiments | Explains voluntary comparison and stopping; template creation collapsed | “n-of-1” and “arm” terminology add background knowledge | Failed API looks like no experiments and invites creation | Manual empty state + failure probe; **medium** |
| Vocabulary/listening | Listening versus reading is explained; adding/importing cards collapsed | To use a deck, learner must remember a setting then start a language block elsewhere | HTTP503 shows both no transcripts and no decks; missing-data claims are not justified | Manual + failure probe; **medium** |
| Materials | Navigation says Materials; screen says Corpus. Import inputs are labelled | Chunks, reranker, trust tiers and instruction flags precede import; operational detail dominates | Invalid path preserved and rejected; allowed-root and not-found errors visible; no job falsely started | Manual two invalid paths + inventory; **high** first-use technical density, **medium** error wording |
| Lesson drafts | Three-step course/section/review flow and local activation meaning explicit | Separate course-based setup alongside Areas increases concept count | Clear distinction between searchable files and activated lessons; source code includes unsaved-edit protection | Manual settled selector + inventory; **medium** |
| Models | Hosted-spend panel appears before model setup; Voice has four explicit steps | Wide model/action table and mixed cost/setup/runtime vocabulary | No download or paid benchmark without action. Registry load failure disappears, while cost failure alone is reported | Manual readiness + failure probe + mobile screenshot; **high** narrow-layout/setup load |
| Preferences | Explicitly reversible settings and adaptation log | Long flat list; raw enum values; retention unit says minutes although label says days | Selected state is visible; save/pending timing less clear. Failed load remains Loading preferences | Prior manual preference round trip + four sizes/failure; **high** decision load |
| Session | Explanation before practice; help, sources, optional confidence, pause/end available | Goal + explanation + action panels + global tools create a tall stack | Pausing preserves place, not elapsed time. Semantic completion and mastery interpretation issues below | Real local tutoring and two incorrect answers; **high** outcome ambiguity |
| Review | Reveal and self-rating distinguish recall from reading; stop remains available | Optional confidence collapsed | Lost-response and pause checkpoints covered in prior suite; no-session entry gives Home recovery | Prior active-flow evidence + current inventory; **low–medium**, full new screen-reader pass open |
| Recap | Optional ratings/notes, explicit finish | No mandatory rating before leaving | Recap-only unsaved fields not made durable; no-session state is recoverable | Source + inventory; **medium** draft-scope limitation, not retested as a populated form |

## Concrete findings

### P2-01 — Failed reads masquerade as loading or empty content

After nine seconds of HTTP503 responses:

- [Preferences](evidence/phase2/preferences-failure.json): only Loading preferences.
- [Map](evidence/phase2/map-failure.json): only Loading map.
- [Vocabulary](evidence/phase2/vocab-failure.json): no transcripts and no decks; invites import/add.
- [Experiments](evidence/phase2/experiments-failure.json): no experiments; invites creating one.
- [Models](evidence/phase2/models-failure.json): cost error shown, registry itself absent without a matching error/retry.

A learner cannot distinguish waiting, having no material, and an unavailable service. Global Home still works, so the audit does not claim a navigation trap. Minimal future correction: distinguish loading/empty/error, keep prior data when possible, offer read-only retry. Do not change model routing or infer absence from a failed read. Validate both initial failure and refresh-after-success.

### P2-02 — Narrow Models page overflows horizontally

At viewport390 the document measured707px: **317px overflow**. Other sampled routes did not overflow at the four tested widths. The full-page screenshot includes content outside the actual viewport; it must not be mistaken for all content being visible without horizontal scrolling. Table actions and full setup text require lateral navigation.

Minimal future correction: contain the table's width or provide labelled responsive rows using existing tokens; keep every model action and readable identifiers. Test390/320,200%text, keyboard access to last column, and large desktop. Do not remove controls or shorten important model identifiers to hide the problem.

### P2-03 — Semantic hierarchy and ARIA are inconsistent

The initial empty-session inventory reports12 of17 routes without a main h1. This is a heading-orientation/best-practice finding, not a blanket WCAG failure. Playground has `aria-label` on an unroled div (axe `aria-prohibited-attr`, at `.mt-4`) at all widths. Validate the intended region before adding semantics; do not mechanically add roles to every div.

Axe also returned incomplete color-contrast checks. No automated contrast violations in this sample does **not** prove contrast everywhere. Touch-target sizing, actual screen-reader announcements and all focus-order permutations remain open.

### P2-04 — “Answer complete” does not mean the request was fulfilled

Three real local explanations ran in the manual sandbox: initial, simpler/confusion, then detailed. [Local-call evidence](evidence/phase2/local-session-observations.json) records Ollama/gemma3:12b and local embeddings, all cost0; no hosted route was called.

The simpler answer supplied a tiny unit-vector example and another step. The detailed request explicitly asked for the formula, magnitudes, angle and a counterexample to “larger dot product always means more similar direction.” The response supplied the formula/geometric relation and a same-direction example, but **omitted the counterexample** and ended with two vectors without a complete task. UI still displayed Answer complete and offered practice. Generation transport completion is being presented in language that can imply instructional completeness.

This sample closes the earlier “never attempted with a ready local model” gap, not the quality-evaluation gate. It does not establish broad model quality or that every detailed reply is truncated. Inspect generation limits, finish reasons and prompt adherence before changing them. Minimal wording must distinguish response received from content verified; a longer-term evaluator should check requested components without claiming certainty it cannot support.

### P2-05 — Wrong answers increased displayed mastery

Manual sequence on the seed skill: Home showed0%; selected incorrect MCQ option9 (correct5), feedback said Not correct and showed10%; next cloze asked about variance/dimension, entered incorrect “colour,” feedback again said Not correct and showed21%. The next question also moved from basic arithmetic to variance terminology without explaining that change.

Read-only sandbox verification: exactly two competency-evidence rows, both deterministic recall score0; final recall state score0.5/count2. Current [competency calculation](../../backend/app/kernel/competency.py) blends recall evidence with mean memory retrievability; coverage increases with evidence count. That explains how the visible estimate can rise despite these wrong answers. It is **not** proof of learner improvement.

This is a larger **learning-model/metric semantics issue**, documented before any implementation. Do not silently clamp scores, alter FSRS, erase evidence or replace the competency algorithm to make UI reassuring. Review the intended meaning of mastery, how new failed review items contribute retrievability, and whether practice exposure is being confused with demonstrated knowledge. Reproduce with fresh wrong-only/correct-only/mixed sequences, delayed review and prerequisite unlocking before choosing a correction. At minimum, the UI must not invite learners to treat this percentage as a test score or unqualified proof of understanding.

The specific feedback was factual and non-punitive; it gave correct answer and a next step, plus Revisit explanation and another question. No forced praise observed. The two-error sample did not demonstrate tailored remediation after repeated misunderstanding; it remains a required evaluation.

### P2-06 — Settings and navigation require unnecessary interpretation

Confirmed previous findings: retention days displayed with a `min` suffix; raw values such as `low_capacity` and `worked_example`; Materials versus Corpus; “arm” in Experiments; choosing both area and course goal. Four-size inspection shows space exists but structure is still task-poor. These are medium/high cognitive-load issues, not permission to flatten all settings or remove expert controls. A grouped progressive-disclosure design needs validation in later phases.

## Required criteria and boundaries

**Orientation:** route titles/current navigation and main focus are strengths; no-session states lead Home. Errors and multiple meanings of progress remain weak.

**Hierarchy:** primary Start/Run and project learning steps are identifiable. Models cost panel, long Preferences list and repeated global tools compete with setup/learning. Desktop max-width prevents unreadably wide prose but creates substantial whitespace; whitespace alone is not a defect.

**Predictability and agency:** explicit sound/playback, confidence optional, own source choices, pause/end and correcting/reporting explanations remain intact. Choice of another question does not explain its jump in conceptual difficulty. Adaptation proposals were not triggered in the manual session; source-level accept/trial/reject/undo is not a usability pass.

**Error recovery:** invalid import paths were rejected without losing the input. Prior unavailable-model request panel exposed technical error/request details; after visiting model discovery, a real local request succeeded. This is evidence of readiness-state sequencing worth investigating, not proof all user's models were broken. Interrupted explanation replay and slow playground stop/retry passed with explicit fixtures. Seven voice-panel tests covered send failure/stop/reconnect and draft preservation; no microphone permission, recording or physical Bluetooth output was tested.

**Interruption:** prior Phase1 checks cover navigation, refresh, browser Back/Forward, active checkpoint resume and late callbacks. Current 16-journey run covers lesson replay, project notebook return, saved-answer keyboard round trip and voice drafts across refresh. Closing/reopening with independent storage and true multi-day recall remain separate; browser-local notes are not universally portable.

**Accessibility:** automated whole-page scan supplements observed focus/label behavior; it is not a screen-reader review. Existing keyboard journeys passed; code editor escape behavior was not re-exercised manually in this phase. Reduced-motion still mode was tested. Native browser zoom, high-contrast settings, every touch target and every dialog still need a complete matrix. Earlier200%text evidence applies to selected flows only.

**Responsive:** measured17 entry states at all four widths; Models overflow reproduced. Inspected four representative full-page screenshots. Dynamic populated lists, every expanded menu and very long translated content are not covered by those entry snapshots.

**Attention and predictability risks:** long setup lists, conceptual naming, secondary tool competition and weak re-entry context create extra work. These are interface properties; no diagnosis or assumption about every neurodivergent person is made. No new gamification, autoplay, unsolicited encouragement or hidden preference changes were introduced.

## Disposition and next phase

Phase2 audit artifact and bounded evidence are complete; remaining acceptance gaps above are explicit. **No production fix was implemented in this phase.** The new code is an opt-in evidence probe only, using already-installed Playwright and axe.

Next incomplete phase is **Phase3 heuristic review**: map these findings plus AU-02…AU-10 to principles and S0–S4 severity, deduplicate, and rank. Treat P2-05 as a learning-model decision requiring explicit analysis rather than a UI-only patch. Do not leap to tokens, prototypes, new runtime providers or broad redesign. The previously queued acquisition work remains separate.

## Review and handoff

Independent source and pedagogy reviews found no major evidence overclaim. The omitted-counterexample finding rests on the recorded manual observation; the database extract verifies model calls and grading/state numbers, not the full prompt/response. No learning-efficacy conclusion follows from this sample. Next: Phase 3 heuristic prioritization, with a separate metric-design investigation before any learning-kernel change.
