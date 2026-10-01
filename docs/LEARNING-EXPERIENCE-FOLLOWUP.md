# Learning experience follow-up plan

Status: **in progress; Q0 completed, Q1/Q2 partially implemented**. Prepared 2026-10-01 after the tutor-focus/conversation fix. This supplements, not replaces, `docs/AUDIT-IMPLEMENTATION-PLAN.md` and existing roadmap. Finish the active slice and its publication gates first. Keep live acquisition/import work separate and avoid concurrent database writers.

## What the report changes

The report's central proposal is a simpler learning loop: resume a meaningful task, understand it with enough context, practise, receive feedback, stop safely and return. It proposes a calmer home, consistent teaching controls, sensory comfort, time cues, source/review transparency and accessible navigation. This is a direction for improving the existing application, not a replacement architecture.

The supplied audit explicitly inspected only the README. Its severity labels are hypotheses, not reproduced defects. Product comparisons and research effect sizes have not been independently verified here; do not repeat them as established evidence or use them to promise learning outcomes. Before using a specific external claim in an ADR or prompt, verify the primary source and population. Do not generalize school/physics studies to an individual adult learner.

Owner choices supersede report suggestions: confidence is optional and collapsed; explicit explanation is the default; Socratic questions are opt-in and reversible; a requested explanation/solution must not become a forced questioning loop. No streaks, forced timers, clinical promises, learning-style labels or mandatory feedback surveys. Preserve area-wide learning across sources. Prefer accurate local execution; no blanket hosted routing change.

## Evidence map

IDs here use **UX26-Fxx**, distinct from the older audit's Fxx IDs. Inspection below is source-level evidence, not a completed usability or WCAG audit.

| Report finding | Current evidence / disposition | Planned follow-up |
|---|---|---|
| F1 setup barrier | README, Makefile and bootstrap still expose technical setup. User-visible burden needs clean-environment measurement. | Q6: capability-specific readiness; packaged launcher deferred. |
| F2 first run | Home exists; Corpus/import and notebook preparation already have guided paths. A new `/today` route is not justified merely by the report. | Q1: test empty/fresh state and put a usable next action first. |
| F3 fragmented readiness | Models and notebook lab have separate readiness/status handling. | Q6: reuse checks, show only dependencies of the chosen action. |
| F4 navigation overload | `frontend/src/app/App.tsx` already groups operator destinations in More tools, with four visible learning/creative links. “Ten equal top-level links” is stale. | Q1: measure task discovery before renaming or regrouping. |
| F5 inspectability | Tutor Response details is collapsed; source disclosure exists in several surfaces. Consistency still unverified. | Q2: concise answer + discoverable exact source; retain material limitations inline. |
| F6 terminology | Home, Areas, Programs, Corpus use different domain terms. Some distinctions are legitimate. | Q1: task-based vocabulary; preserve expert names in help. |
| F7 next action | `routes/Home.tsx` has a primary resume/start action but configuration precedes it. | Q1: checkpoint/next-step card before optional setup. |
| F8 timing | `features/session/SoftTimer.tsx` has server-derived deadline, extend and save/stop. `Session.tsx` shows planned minutes. | Q4: optional position/remaining-time cues, no replacement clock or forced transition. |
| F9 parking | `components/ParkingLotButton.tsx` is global and supports Enter; no global hotkey in this component. Existing reliability audit already covers failed/double saves. | Q4 after existing reliability fix: optional shortcut and focus restoration; avoid command-palette conflicts. |
| F10 conversation | Current slice adds target selection, visible history, feedback follow-up and clear Socratic mode. Prompts already request examples and steps. | Q2: adaptation controls and concise response contract; evaluate local model before changing schema. |
| F11 fallibility | `routes/Session.tsx` already exposes Report this explanation as wrong; content correction workflows exist. | Q3: map report/review lifecycle before considering another Dispute table. |
| F12 latency | StudyTutor has busy, Stop, timeout, request identity and retained draft; main tutor has streaming recovery. | Q2: consistent elapsed status and completed-message announcements, no invented ETA. |
| F13 imports | Per-item progress and archive resume exist; long individual conversions remain limited. | Q6: elapsed/liveness and explicit recovery; never call a slow job dead solely from elapsed time. |
| F14 tokens | `frontend/src/index.css` already has theme tokens, focus ring and shared reading styles. | Q5: inventory drift, contrast and token use rather than introduce a second system. |
| F15 responsive layout | Shell has wider notebook/playground layouts; browser journeys already test narrow screens. | Q5: add 700/900px, 200% zoom, actual overflow/focus checks. |
| F16 global comfort | Global OS reduced motion, `.reduce-motion`, theme, density and font scale exist; `useSensory` runs in Shell. Claim of no global settings is contradicted. | Q5: close verified gaps; one preference authority, no duplicate Zustand store. |
| F17 accessibility | Existing axe-core/vitest-axe and editor/voice/source tests are present. Automated checks do not certify WCAG or screen-reader behavior. | Q5: full learning loop, widget keyboard/focus and manual VoiceOver. |
| F18 shortcuts | Notebook execution and editor journeys exist; remapping/shortcut overview needs inventory. Shift+Enter is not a single-character shortcut. | Q5: document actual bindings, escape paths and configurable conflicts. |

## Execution contract

Use the repository's feature-slice workflow and current owner publication policy. Read the latest handoff before each phase. Resolve overlapping older audit items instead of implementing duplicate fixes. Each bounded slice needs a reproduction or observable baseline, state ownership, failure/recovery behavior, tests, independent code/pedagogy review where applicable, and an updated handoff. No new dependency, schema, endpoint or provider is required merely because the report suggested one.

Use synthetic material and fake models for regression/browser journeys. Run relevant tests, lint/types and production build for UI slices; backend/migration checks only when touched or required by project rules. A fake-model pass proves the interaction contract, not teaching quality. Keep local model evaluation a separately reported gate. Fresh public installs must contain no learner database, acquired material, account identifiers or acquisition tools. Keep original report private; publish only generic plan/skills/code under the established two-repository workflow.

### Q0 — Finish current conversation slice

Dependency: none. Status: completed and verified (184 frontend tests, 421 backend tests, lint/types/build, three isolated browser cases and required reviews); see `docs/slices/study-tutor-conversation.md`.
Acceptance: choose a notebook step without moving/executing the editor; know what is being discussed; answer one Socratic question then receive feedback; continue after answer review; switch targets and restore unsent drafts; stop/stale responses cannot overwrite work. Desktop/narrow keyboard journeys and existing storage-failure regressions. Commit this independently before Q1.

### Q1 — Resume first, fewer decisions

Coverage: UX26-F2/F4/F6/F7. Dependency: Q0. Status: partial — Home resume card implemented; see docs/slices/home-resume-card.md. Broader onboarding, notebook checkpoints and terminology tasks remain.
Start with `routes/Home.tsx`, `app/App.tsx`, session checkpoint/selection APIs, prior audit R1 and Home tests. Put one primary resume/start card above optional settings, showing real area, last task and next small action. Offer short review and change topic as secondary actions. Empty areas explain what is missing and link to the correct source/setup screen; never substitute a random skill. Keep existing routes/deep links.

Acceptance: fresh learner, active lesson, stopped lesson, notebook task and unavailable source states each have an honest primary action; reload resumes correct topic; changing topic does not erase work; keyboard and 390/800/1280px work. Baseline time-to-first-useful-action locally; <60s is a hypothesis, not a promise. Create a small glossary in the slice doc rather than mass-renaming every technical noun.

### Q2 — Predictable teaching and controllable waiting

Coverage: UX26-F5/F10/F12. Dependency: Q0; can follow Q1. Status: partial — current-response adaptation controls implemented; see docs/slices/tutor-explanation-controls.md. Local model adherence remains partial, elapsed/announcement/source work remains open.
Reuse StudyTutor, common Markdown, source viewer, local routing and streaming recovery. Offer Shorter, Smaller steps, Example and Explain instead against the current target, preserving the conversation. Keep brief answer/example/next action structure where useful; do not force every reply into five empty headings. Use the existing output contract first; only propose structured JSON after local-model compatibility/evaluation evidence. Show immediate pending state, elapsed time and Stop without an unsupported estimate. Announce completed replies, not every token.

Acceptance: controls stay on selected step; no hidden mode switch; delayed/error/stopped reply retains drafts; sources open the matching passage when available and unsupported claims remain labeled; answer checking discusses actual answer before a follow-up. Test long answers and changed code. Separate synthetic contract tests from a local-model rubric: directness, relevance, source honesty, one-question pacing and useful feedback. Preferences never count as mastery.

### Q3 — Trust and correction end to end

Coverage: UX26-F11 and existing content-correction audit. Dependency: Q2.
Inventory current content_report, assessment and correction/re-grade APIs first. Add consistent “Something is wrong” access to tutor feedback and graded items only where missing, showing criteria and relevant sources. Preserve original answer, disputed outcome and resolution; deterministic checks first. Different-model re-grading is not an automatic paid fallback. If new durable state is needed, prepare a bounded ADR/schema migration with rollback and learner scoping.

Acceptance: report remains visible after reload, double submit/retry does not duplicate evidence, disputed and upheld outcomes are distinct, correction does not silently rewrite mastery, no unsupported citations, no paid call without applicable authorization. Include current unanswered-report state and recoverable errors.

### Q4 — Optional time cues and tangent capture

Coverage: UX26-F8/F9. Dependency: Q1 plus existing parking reliability work.
Extend SoftTimer's server-based clock; optional hideable timeline/countdown and gentle boundary cue. Keep extend/stop available; hidden tab/reload/clock changes cannot duplicate cues or evidence. Add a configurable modifier shortcut only after checking browser/editor collisions; preserve focused field, text, selection and unsaved code when opening/closing capture. No default Cmd/Ctrl+Shift+P without conflict testing.

Acceptance: timer off stays off, stop is never gated, background/foreground transitions are sane, failed parking save retains text and repeated Enter sends once; escape returns focus to exact caller. No forced survey, sound, animation or domain switch.

### Q5 — Comfort and accessibility coverage

Coverage: UX26-F14/F15/F16/F17/F18. Dependency: Q1/Q2; incorporate Q4 if already implemented.
Extend existing sensory preferences/tokens and controls. Inventory all audio/motion surfaces, narrow overflow, target sizes, focus order, contrast and editor escape guidance. Reuse installed axe-core; an extra Playwright adapter is optional and needs a concrete benefit/license/version check. Additional fonts and high-contrast themes are optional separate slices after actual need and contrast testing, not presumed treatment.

Acceptance: complete choose/learn/practise/feedback/stop/resume keyboard journey, 390/800/1280px and 200% zoom; no serious/critical automated findings in scoped fixtures; reduced motion still allows measurement, sound remains opt-in. Manual VoiceOver outcome recorded separately, never inferred from axe. Storage/backend failure must not reset active comfort preferences silently.

### Q6 — Readiness and calm progress

Coverage: UX26-F1/F3/F13 plus report recommendations 11/13. Dependency: Q1/Q5.
First slice: reuse current readiness checks for a contextual checklist; reading downloaded material must not require all model/voice services. Second slice: honest elapsed/liveness for long imports and safe recovery after confirmed worker loss. Third slice: progress expressed as demonstrated tasks, due workload with measured/explicitly estimated timing, and uncertainty. Do not equate a bookmark or model opinion with competence. Packaged launcher is a separate future decision; don't add a menubar app now.

Acceptance: service-off cases have one relevant repair action; no secret leakage or arbitrary shell execution; slow conversion never gets a competing writer from Retry; recovery respects latest archive-member outcomes. Fresh public DB can start a generic sample without private content. Progress distinguishes attempted, independently checked and needs-review.

### Q7 — Evidence-backed tutor and learning evaluation

Coverage: report recommendation 12 and validation proposals. Dependency: Q2/Q3/Q6.
Use existing isolated Python runner/check infrastructure for learner-authorized experiments; never automatically run arbitrary notebook/tutor code in the host scientific kernel. Attach “checked” only to the exact input/code/environment/output tested, invalidate on edit and keep exceptions visible. Citation presence is not proof of support. Start with one curated generic area and a local rubric/evaluation set. Optional N-of-1 study requires agreed measures and a separate protocol; no mandatory daily ratings or recruitment implied by this plan.

Acceptance: changed code loses its check badge; timeout/unsupported library yields unchecked, not incorrect or mastered; source passage actually supports cited claim in reviewed samples; record local latency and correctness separately. Independent delayed-transfer evidence remains open until measured. Local study tracking never fabricates external attendance or degree credit.

## Reusable execution prompt

```text
Implement the next eligible bounded slice of phase Q<N> in docs/LEARNING-EXPERIENCE-FOLLOWUP.md. Read AGENTS.md, CLAUDE.md, latest HANDOFF and the existing audit/roadmap status first. Use audhs-experience-followup; for tutor verification use audhs-tutor-evidence. Reconcile UX26 finding IDs against current code and prior completed work. State the narrow delta and acceptance cases, then implement and verify with isolated data and local/fake providers. Preserve source provenance, optional confidence, explicit-first teaching, stop/resume and existing preference authority. Obtain required reviews; report model/browser/manual gates separately. Update the phase and handoff with exact commands/results, remaining gaps and next slice. Follow current owner commit/publication policy; keep private material and databases out of public. Do not implement subsequent phases automatically or add a service/dependency merely because the report proposed it.
```

## Next action and decision record

Next eligible implementation after Q0: **Q1, Home resume card only**, not a broad navigation rewrite. No new API decision yet; inspect available checkpoint data first. Q2's response-format change, Q3 schema changes, extra fonts, launcher packaging and automatic verification runtime remain evidence-dependent decisions. The skills/plan are deliverables now; new redesign implementation remains queued.
