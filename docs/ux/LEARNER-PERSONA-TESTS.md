# Learner persona tests — Phase 4

2026-10-04. Behavioral profiles guide an expert walkthrough; these are not diagnoses, recruited participants or evidence that a particular population finds the interface easy. No application or learning-policy change was made. Findings build on [Phase 2](UX-AUDIT.md) and [Phase 3](HEURISTIC-REVIEW.md).

## Method and scope

Ran the seeded disposable application through 14 browser checks: two new persona probes, three session journeys, four Home/resume cases, two assessment recovery cases, one session-clarity case and two notebook tutor conversations. The real sandbox handles deterministic sessions, checkpoints and assessment writes. Home-specific cases and tutor-response cases include explicit synthetic fixtures. No paid inference was requested; these tests do not evaluate generated explanation quality. Phase 2's actual local-model sample remains the semantic evidence, with its limited scope.

The new probe follows Home → Start → plan → skip movement → finish due review → learn; types an unfinished confusion request; saves/undoes a clear label; keyboard-pauses; resumes; reloads; and resumes in an independent browser context. It runs at 1280px and 390px. First run passed all 14. Review found the Home text capture could precede the refreshed checkpoint query; the probe now waits for the displayed teach phase before recording evidence, then was rerun. That observation was not counted as a persistent wrong checkpoint.

These flows automate intentional actions, not human cognition. Click counts below exclude fixture preparation and variable due-card ratings. A fresh browser context tests absent client storage, not one week of elapsed time or ordinary reopening of the same browser profile. Tests do not claim browser-local drafts should synchronize across devices.

## A — Distractible learner

**Intent:** begin quickly, perform something useful, leave and return without reconstructing the task.

**Observed sequence:** Starting from Home requires Start session → choose plan order → optional movement/Skip → review/Continue before the learn screen. On an empty review queue that is four primary clicks before requesting an explanation; due cards add interactions. The new probe does not generate an explanation or demonstrate completion of a learning activity. Existing deterministic assessment/review journeys supply separate evidence that an activity can be checked or rated. Pause is one button; Home exposes a topic-named Resume; same-browser resume and reload retain the unfinished request and checkpoint.

**Friction/confusion:** starting learning includes plan overhead even when the intention is a specific lesson. On the resumed desktop screenshot, task controls and learning-goal/audio panels precede the explanation action. The learner may have to scroll to resume meaningful content. Activity 3 of 4 can look like substantive progress despite only passing preparatory blocks.

**Unnecessary decisions / memory:** plan ordering, review versus new material, then explanation versus another help action. Home restores topic and phase but not a concise last-idea summary; the learner still recalls what was confusing.

**Missing feedback:** there is no durable cross-context notice for the unfinished question in the tested fresh context. Do not interpret server checkpoint retention as retention of all draft text.

**Positive patterns:** explicit pause/end distinction; no rating required to pause; keyboard Resume; preserved draft within its existing storage scope; optional preparatory block.

**Recommendation:** retain this recovery contract, measure time to first useful explanation with a human, and reduce competing setup information through later IA rather than deleting preparatory capabilities. HR-08/HR-11 apply.

## B — Detail-oriented learner

**Intent:** inspect the concept, request precision, see progress and understand recommendation effects.

**Observed sequence:** Phase 2 manually requested a formula, magnitudes, angle and counterexample. The local answer supplied some requested detail but omitted the counterexample while labelled complete. The current notebook conversation checks verify focus/history retention, switching Socratic to explicit discussion and keyboard Shorter/Smaller steps/Example requests; their response text is synthetic. They establish interaction contracts, not successful pedagogy. Prior manual Preferences navigation/text-size change retained the lesson draft; this phase did not repeat every preference effect.

**New observation:** the first combined run's narrow Home screenshot showed an adaptation proposal after accumulated sandbox early exits: plan 15 rather than 20 minutes, with a reason based on the last three new-material blocks. Try this session, Make it the default, No and Don't suggest this again were visible. It also exposed `planner.new_material_min`. This was a genuine sandbox-generated proposal influenced by preceding test activity, not a human behavior inference. Acceptance/trial/rejection/undo were not exercised here.

**Friction/confusion:** raw setting names and unspecified effect on the already-paused plan demand internal knowledge. Completion wording does not indicate whether requested details were checked. A single mastery percentage obscures the evidence/retrievability distinction.

**Unnecessary decisions / memory:** choosing a temporary versus persistent change before understanding scope; remembering exactly which requested explanation components were absent.

**Missing feedback:** content coverage, the basis of displayed mastery and current-versus-next-plan effect remain unclear. A visible reason does not prove an adaptation is appropriate.

**Positive patterns:** explanatory reason and rejection controls exist; focused conversation retains target and unsent text; sources and optional detail remain accessible.

**Recommendation:** validate adaptation effect timing with a seeded proposal test; translate internal setting names; keep requested-detail evaluation separate from transport status. HR-01/03/10 apply. The earlier adaptation hypothesis is now partly observed (presentation), not fully closed (behavior).

## C — Anxious beginner

**Intent:** encounter an unfamiliar topic, make an error, ask for help and continue without pressure.

**Observed sequence:** Phase 2's actual two wrong answers produced factual correction and correct-answer information, with learner-controlled next/help choices. Its simpler explanation gave a small numerical example. Current session-clarity checks verify an explanation-first option, hint, source opening/closing with focus restoration and collapsed optional confidence. Current desktop/narrow interrupted-assessment checks recover one committed result after a deliberately lost reply, without a second submission. Hint content and some recovery lookup states are fixtures.

**Friction/confusion:** the next question in the Phase 2 sequence jumped from arithmetic to variance. Incorrect answers coincided with rising mastery, potentially implying successful understanding. Technical service errors may require knowledge the beginner lacks.

**Unnecessary decisions / memory:** which help surface explains the current mistake; distinguishing a checked original answer from a new attempt during recovery.

**Missing feedback:** why the question changed conceptual level and what to revisit next. The tests do not establish how safe or encouraged a human feels.

**Positive patterns:** factual correction, optional confidence, preserved original feedback, available hint/source and stop paths. No shaming was observed in the sampled feedback.

**Recommendation:** evaluate contextual remediation on held-out examples; explain progress honestly before adding praise or motivation. Preserve the single-submission recovery contract. HR-01/02/06/07 apply.

## D — Advanced learner

**Intent:** bypass known material, demonstrate knowledge and move ahead efficiently.

**Observed sequence:** movement can be skipped; initial plan can prioritize review. The new probe clicks This is clear, sees the saved-label notice, verifies the server checkpoint did not advance, and undoes the label. Session-clarity confirms labels can be revisited after changing topic. Current assessment tests prove deterministic answers can be submitted/recovered, but do not demonstrate an advanced learner bypassing prerequisites or unlocking a later topic through prior knowledge.

**Friction/confusion:** a clear label is easy to interpret as “move on,” although explanatory text correctly disclaims mastery. Revisit opens a session plan. There is no verified direct prior-knowledge demonstration journey in this evidence.

**Unnecessary decisions / memory:** distinguish bookmark, skip, assessed mastery and topic change; remember where the next relevant material is.

**Missing feedback:** an obvious separate action after marking material understood. Whether an advanced placement flow is a product requirement must be determined before inventing one.

**Positive patterns:** no unearned mastery from labels; Undo; preparatory Skip; assessment remains available independently of self-rating.

**Recommendation:** clarify saving versus moving on. Investigate the existing assessment/unlock contract before proposing any fast-track flow. Do not award mastery from a bookmark or remove prerequisites for convenience. HR-08/09 apply.

## E — Returning learner

**Intent:** reopen after time away, recognize the previous topic and continue.

**Observed sequence:** new probe resumes in the same browser, refreshes, then opens an independent context. The same server topic/checkpoint returns in both contexts. The same-context unfinished request survives; the independent context's field is empty. Existing session journey also resumes from a fresh context at a saved block boundary. Home fixture tests verify named topic and next review step at 390/800/1280px.

**Friction/confusion:** “teach” appears as a technical phase label. Resuming an ungenerated lesson restores the goal and Start explanation rather than a recap of what was learned. Draft storage and server progress have different scopes.

**Unnecessary decisions / memory:** Resume competes with Start and new-session targets. The learner remembers the previous question or intention when it was only an unsent local draft.

**Missing feedback:** no verified last-idea/last-question recap; no actual week-long absence study. No claim about retention, expiry or user recall after a week is justified.

**Positive patterns:** server restoration does not depend on local session IDs; current topic named; saved work not replaced by a default topic; settings for new sessions are distinguished from the existing session.

**Recommendation:** validate a concise factual re-entry summary from persisted evidence, clarify draft scope where needed, and conduct the actual delayed-return check. HR-08/11 apply.

## Cross-profile outcome and next phase

Common strengths: explicit pause, checkpoint ownership, optional confidence, reversible labels, focused tutoring context and interrupted-submission recovery. Common unresolved costs: plan/setup before content, opaque progress, different meanings of saved state, and implicit action consequences. No persona received a fabricated satisfaction or learning score.

Phase 4's expert walkthrough is documented; human validation remains open. Phase 5 should derive the information architecture from these tasks: resume a learning intention, understand before answering, obtain contextual help, find prior material and distinguish progress from activity. Keep advanced controls, provenance and modalities available through appropriate disclosure. Do not implement a new runtime architecture or redesign unrelated screens in this phase.

## Verification record

Initial combined run: 14/14 passed. After tightening the observation point to wait for the refreshed teach-phase label, final new probes: 2/2 passed. Focused ESLint passed. Evidence: [desktop observations](evidence/phase4/persona-1280.json), [narrow observations](evidence/phase4/persona-390.json), [Home desktop](evidence/phase4/return-home-1280.png), [Home narrow](evidence/phase4/return-home-390.png), [fresh context desktop](evidence/phase4/fresh-context-1280.png), [fresh context narrow](evidence/phase4/fresh-context-390.png). Screenshots inspected; keyboard Pause/Resume and document-width checks passed. These final isolated screenshots do not retain the adaptation proposal from the initial combined run; that finding is a recorded visual observation, not independently replayable from these images.

Reproduce: `AUDHS_UX_AUDIT=1 pnpm --dir frontend exec playwright test e2e/learner-persona-audit.spec.ts`. The new probes are opt-in and skipped in ordinary CI. No production build was required for this test/documentation change.

Visual follow-up: the fixed Park control overlaps explanation text in the narrow full-page capture. This warrants a scrolled-viewport/focus check in later layout work; the absence of horizontal overflow does not prove content is unobscured. The primary explanation action is below the initial 900px viewport on the narrow resumed screen. No control was removed or repositioned in this phase.
