# Local operational notes

Personal inventories, execution logs and handoff history are kept outside the public repository.

## Chunked session reading — 2026-10-01
Completed explanations support section/full reading, recoverable notes with inspectable citations, and optional reasoning requests preserving drafts. Versioned prompt supports readable sections; navigation and large-text layout improved. Backend378/frontend168, lint/types/build and three isolated browser journeys pass. Independent review found no remaining blockers/majors. Model compliance, actual microphone and learner outcomes remain unmeasured. No runtime data or private sources included.

## Silent video outcomes — 2026-10-01
Optional ffprobe checks MP4/M4V/MOV/MKV/WebM/AVI before speech decoding. Confirmed video-only streams become no_content; unknown/malformed/failed probes retain decoder behavior. Original assets unchanged. 390 backend tests and full lint/types pass; independent review no blockers/majors. Other video suffixes keep prior behavior. Existing running worker is deliberately not restarted; historical run errors remain intact, new workers use the improved classification.

## XML project configuration — 2026-10-01
Non-caption XML now imports as validated source code, retaining existing TTML behavior and source provenance. DTD/entity declarations rejected; obvious credential fields redacted; originals unchanged. 396 backend tests/lint/types pass, independent review no blockers/majors. Selective local recovery imported 110 documents and indexed 276 nonduplicate chunks; generated/oversized/unsafe files remain flagged. Existing bulk process remains running with its original loaded code.

## Shared audio controls — 2026-10-01
Global and inline volume/mute/speed controls plus explicit sound test. System-selected output guidance; no automatic microphone activation. Voice rate retained across delayed chunks until a new response; media speed live; analysis remains independent of output gain. 173 frontend tests, 396 backend tests, full lint/types/build and isolated Chromium audio journey pass. Independent review major fixed, re-review no blockers/majors. Hardware Bluetooth audibility is unverified. See docs/slices/shared-audio-controls.md.

## Task notebook round trip — 2026-10-01
Try can open a section-specific local starter with a CSV, separate inspectable calculation checks, and return checked output to preserved project notes. Edits invalidate success; Back remains available. 177 frontend tests, lint/types/build, isolated real-Pyodide Chromium journey and required code/pedagogy re-review pass. No new backend API or progress claims. See docs/slices/task-notebook-roundtrip.md.

## Inline answer feedback and question audio — 2026-10-01
Think deeper exposes Check my answer using the existing session/tutor routing; question, criteria and worked example are supplied. Selected question, revealed hint/checklist and returned feedback have explicit listening controls. Edits invalidate old feedback; text changes stop/reset speech. 180 frontend tests, lint/types/build, isolated fake-tutor Chromium journey and required reviews pass. Real model correctness and headphone audibility are not certified. See docs/slices/project-answer-feedback.md.

## Local notebook lab from app — 2026-10-01
Notebook workspace can prepare an explicit private bundle, preserve existing edits, install/repair pinned base tools on request and start loopback authenticated Jupyter. No cells execute automatically. Eight backend regressions, 181 frontend tests, lint/build, isolated browser journey and code/pedagogy reviews pass; real launch returned ready and HTTP 200. Course-specific legacy dependencies remain a separate compatibility task. See docs/slices/local-notebook-launch.md.

## Diagram text ingestion — 2026-10-01
Bounded decoding of compressed/plain draw.io files preserves labels, explicit connector endpoints and attached labels. HTML headings are retained; scripts, entities and expansion bombs are rejected or excluded. Visual/arrow semantics are explicitly not inferred. 418 backend and181 frontend tests, lint/types and required re-review pass. No runtime data or private acquisition sources included.

## Notebook package cells — 2026-10-01
Both local launchers now include pinned pip and activate the environment PATH for notebook shell commands. API readiness detects a missing pip module and offers repair. Real isolated kernel package-cell checks,419 backend tests,lint/types and review pass. No learner notebook cells were edited or executed. Prefer %pip for the active kernel; already running servers need relaunching for updated shell PATH.

## Archive-member retry — 2026-10-01
Resume now uses latest outcomes across its chain and reopens archives containing retryable members, preserving successful members. Two synthetic repeated-failure regressions pass;421 backend tests,lint/types and code review pass. Existing running workers retain their loaded code. See docs/slices/archive-retry.md.

## Tutor focus and conversation — 2026-10-01
Named notebook-step focus, target-specific history and drafts, feedback follow-up and clear opt-in Socratic replies. 184 frontend/421 backend tests, lint/types/build, three isolated browser cases and independent code/pedagogy review pass in the source checkout. Live-model teaching quality and manual VoiceOver remain separate gates. See docs/slices/study-tutor-conversation.md.

## Queued learning-experience follow-up — 2026-10-01
Read the supplied README-only audit in full and reconciled all18 findings against representative current code. docs/LEARNING-EXPERIENCE-FOLLOWUP.md separates contradicted/partial/unverified claims and queues Q1–Q7 after completed Q0. Two validated skills are available in .claude/skills: audhs-experience-followup and audhs-tutor-evidence. Copies installed for Codex discovery locally. Next bounded slice: Q1 Home resume card, preserving existing routes and real checkpoint state. No new redesign code or dependencies in this planning change. External research claims remain unverified; optional confidence supersedes the report's recommendation. Original report remains private.

## Home resume card — 2026-10-01
Primary saved-topic/next-action card now precedes setup; session options are collapsed. Failed server lookup suppresses stale-browser Resume and offers Retry. 186 frontend tests, lint/types/build, four isolated browser cases and code/pedagogy review pass. Q1 remains partial: broader onboarding/project checkpoint work is separate. Session-clarity journey surfaced an unrelated duplicate-key warning for later diagnosis. See docs/slices/home-resume-card.md.

## Visuals kits assessed and queued — 2026-10-01
Two supplied archives assessed as proposals, not installed instructions. First queue covers validated visuals, local model evaluation, optional authored blocks and curated resources; second adds read-only codebase explanations with immutable evidence. Second archive retains all first-kit plans/benchmark unchanged and adds self-explanation. Five scoped skills validated and installed for local Codex plus shared Claude use. See docs/VISUAL-LEARNING-QUEUE.md and docs/SELF-EXPLAIN-QUEUE.md for task dependencies, acceptance gates, corrections and execution prompts. No new model/provider/dependency/index/feature activated. Originals and validator probes remain private. Resume existing Q work and acquisition recovery before treating these queued branches as active.

## Queued saved tutor answers — 2026-10-01
Owner requests database-persisted, searchable prior tutor answers and suggested Q&A per course. docs/TUTOR-ANSWER-LIBRARY-QUEUE.md defines QA00–QA05 with area/step scoping, provenance, completed/partial status, correction/staleness, zero-model-call reuse and private backup. Browser conversation storage and TutorTrace metadata do not already fulfill this. Coordinate with Q2/Q3 and A01; no implementation started.

## Tutor explanation controls — 2026-10-01
Current completed replies offer Shorter, Smaller steps and Show an example; preserve target/history/draft, hide on stale work, and require Explain instead before leaving Socratic mode. 188 frontend/421 backend tests, lint/types/build, two isolated desktop/narrow keyboard journeys pass. Code/pedagogy review has no blockers/majors. Local three-case sample exposes remaining brevity/code-format limitations, documented with raw synthetic outputs; no general model-quality claim. Q2 remains partial. See docs/slices/tutor-explanation-controls.md.

## Tutor waiting and completion — 2026-10-01
StudyTutor now shows quiet elapsed waiting beside Stop above the conversation and a concise completed-response announcement. New tests cover Stop/retry/late completion, timeout, draft retention, restored history and clock cleanup. 191 frontend tests, lint/types/build and three isolated browser cases pass; independent code/pedagogy review has no blockers/majors. Backend unchanged (prior421-test baseline); manual VoiceOver unverified. Q2 remains partial: other tutor surfaces, source consistency and model-quality work remain. See docs/slices/tutor-waiting.md.

## Notebook input width / CI follow-up — 2026-10-01
Public CI found390px horizontal overflow. Reproduced with larger native file-picker text; constrained input width and notebook-card minimum width without hiding overflow. All33 local browser journeys, lint/types/build and independent code review pass. Linux CI confirmation follows publication; existing session duplicate-key warning remains separately queued. See docs/slices/notebook-responsive-input.md.

## Assessment widget identities — 2026-10-01
Fixed the observed duplicate-key warning: question help and question feedback are sibling widgets and now have distinct role-prefixed assessment keys. Failing browser regression reproduced three warnings before the change, now passes with feedback draft retained during answer edits and one hint control. 191 frontend tests, lint/types/build, four session journeys and independent code review pass. No backend/grading/prompt changes. See docs/slices/assessment-widget-identity.md.

## Shared tutor status and cancellation — 2026-10-01
Shared quiet elapsed/completion status now covers notebook/project StudyTutor, streamed lessons, assessment help and standalone coding playground. Playground Stop/timeout settles immediately even if transport ignores abort; late callbacks cannot replace retry results. Browser-discovered delayed focus race fixed with generation and active-control checks. 196 frontend tests, lint/types/build and seven relevant browser cases pass across final reruns; required code/pedagogy reviews clear. Prior assessment commit14d2545 is fully green in public CI. Manual VoiceOver, source consistency and model-quality gates remain open. See docs/slices/shared-tutor-status.md.

## Tutor source access — 2026-10-01

Hints and lesson explanations share inspectable sources with turn identity, flags, source reporting and Close focus restoration. StudyTutor source limits are visible. Temporary passage failures offer retry without implying removal; failed refetch does not display stale cached text. 199 frontend tests, lint/types/build and isolated keyboard assessment journey pass. Independent code/pedagogy review clear. Q2 remains partial; saved-answer library queued. See docs/slices/tutor-source-access.md.

## Saved-answer library QA00 — 2026-10-01

Answer-path inventory and proposed ADR-0017 prepared. Design covers shared lesson/voice output, workspace scope, representation snapshots, assessment references, retry/ownership and backup boundaries. Independent code/architecture and pedagogy review clear. No database migration or feature activation; QA01–05 remain pending. See docs/design/tutor-answer-lifecycle.md.

## Tutor ownership prerequisite — 2026-10-01

Tutor stream/turn and representation render/prefer validate the local owner before using session context. Foreign/missing IDs produce equivalent errors and no model calls or learning writes. 425 backend tests, lint/types and independent code/pedagogy review pass. Answer persistence remains pending. See docs/slices/tutor-session-ownership.md.

## Additional document queue — 2026-10-01

Initial triage of three owner documents completed; originals retained privately. Generic queue in docs/LEARNING-VOICE-DOCUMENTS-QUEUE.md covers evidence verification, provenance/sharing controls, source freshness and a separate optional avatar/voice prototype with explicit handoff. Claims remain unverified; no device access, acquisition, scheduler or new feature enabled. Saved-answer work retains priority.

## Saved workspace answers — 2026-10-01

QA01 partial: completed workspace tutor answers persist in learner-scoped SQLite with bounded request/model snapshots. Save errors preserve reply text and display warning; learner/turn save uniqueness rejects conflicts. 428 backend,200 frontend tests,lint/build,5 isolated browser journeys and code/pedagogy review pass. Populated backup/export/wipe and migration on disposable data verified. No runtime data included here. Request-level retries, other response paths, stable course/step IDs and search/suggestions remain pending. See docs/slices/saved-workspace-answers.md.
