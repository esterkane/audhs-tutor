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

## Saved lesson answers — 2026-10-01

Completed shared tutor replies now persist final text with source hashes/citations and selected skill/area. Partial/aborted generation excluded. Lesson/hint/voice panels show save status; completed stream and voice text match canonical saved response. 430 backend/202 frontend tests, lint/build and independent review pass. Request-level recovery, workspace scope, other history paths and search remain pending. See docs/slices/saved-lesson-answers.md.

## Publication guard hardening — 2026-10-01

Guard checks indexed blobs, runtime/private snapshot paths and prohibited source tokens; clean unstaged copies cannot hide staged private content. Three regression tests, lint/types and independent review pass. Current staged public index verified. Publication commands must stop on guard failure. No runtime feature change. See docs/slices/publication-index-guard.md.

## Answer history API — 2026-10-01

Read-only owner-scoped list/detail routes expose completed saved snapshots with bounded cursors and skill/area/surface filters. Foreign/missing IDs and cursors are indistinguishable; no generation or evidence changes. Independent review clear. Full-text search, UI and suggestions still pending. See docs/slices/answer-history-api.md for verification.

## Saved-answer browser — 2026-10-01

Saved reply links and More tools → Saved answers provide paginated filtered history and exact saved context. Historical conversation and source qualifications retained. Six focused tests, two isolated Chromium desktop/narrow keyboard journeys, lint/types/build and independent code/pedagogy re-review pass. Search/suggestions remain pending. Both repositories must remain private; sanitized release safeguards stay enabled. See docs/slices/answer-history-ui.md.

## Local saved-answer search — 2026-10-01

SQLite FTS5 searches saved request labels and completed answers, with literal all-word matching, owner isolation and existing filters/cursors. Explicit browser search preserves the query on return. Backfill and transactional triggers cover writes/deletion; restored backups remain searchable. 436 backend/209 frontend tests, lint/types/build, two isolated desktop/narrow journeys and independent code/pedagogy review pass. Remaining: stable course/step metadata, suggested Q&A, follow-up and lifecycle/correction gaps. Both repositories stay private. See docs/slices/answer-search.md.

## Contextual saved replies — 2026-10-01

Guided section/task/saved notebook tutor requests carry optional bounded course/section/target IDs and actual learner questions separately from action prompts. Explicit “Previously answered here” loads exact-target history with source-age/code caveats and scoped browsing links. Navigation metadata is not model evidence. 436 backend/211 frontend tests, lint/build, four isolated desktop/narrow journeys and independent code/pedagogy review pass. Remaining: broader course/area suggestions, linked follow-up, validated manifest scope and freshness/correction. See docs/slices/answer-context.md.

## Course/area saved-answer overviews — 2026-10-01

Selected course and learning-area pages expose explicit scoped saved-answer panels. Missing scope never fetches global history; area history spans surfaces. Full frontend suite, lint/types/build, three isolated browser journeys and independent code/pedagogy review pass. No backend change. Linked follow-up and freshness/correction remain next. See docs/slices/answer-overviews.md.

## Saved-answer follow-up — 2026-10-01

Owned saved answers now support explicit bounded follow-up through the local-first gateway, active-session validation and persisted parent/context snapshots. UI includes draft+parent recovery, Stop/timeout, error/save status, optional audio and parent/history links. 437 backend/217 frontend tests, lint/build, four desktop/narrow browser journeys and independent review pass. Historical answers are not source evidence; immediate parent only, bounded excerpts and omissions visible. No mastery changes. See docs/slices/answer-followup.md.

## Saved-answer feedback — 2026-10-01

Separate owner-scoped revision-checked reports preserve immutable answers. Helpful/confusing/incorrect/outdated labels, optional reason and hidden state are explicit/reversible; contextual suggestions omit hidden/incorrect/outdated items while history retains them. Follow-up warnings and historical report target the actual resumed parent. Full backend438/frontend219 suites plus final focused concurrency and warning regressions, lint/build, four desktop/narrow browser journeys and independent re-review pass. Backup/restore and two-learner export/wipe cover the new table. No automatic training/mastery or verified correction. Source freshness, actual correction/replacement and save-retry lifecycle remain queued. See docs/slices/answer-feedback.md.


## 2026-10-01 — saved-source comparison

Added explicit owner-scoped, bounded local source hash checks to answer history: changed, unchanged, missing, unverifiable and newer-version notices. No model call or evidence write; unchanged text does not certify truth. Verification: 440 backend, 221 frontend, two isolated browser journeys, lint/types/build; independent code/pedagogy review clear. Next: bounded retrieval before generation, exact-context reuse, then evaluated local semantic search. Both repositories remain private.


## 2026-10-01 — workspace answer memory

Workspace tutor requests now retrieve up to two bounded historical excerpts before generation using local literal search, owner/target/exact supplied-work/intent filters and negative-feedback exclusions. Memory-assisted replies are not recursively reused. Retrieval SQL failure falls back to normal generation. Prior excerpts/dates/links persist and remain inspectable after reopening; they are not independent evidence. No automatic replay or measured performance win. Verification: 442 backend, frontend suite plus 26 focused post-review tests, lint/types/build and isolated desktop/narrow notebook journeys; code/pedagogy re-review clear. Next: local quality/latency evaluation, explicit direct reuse and semantic search; main streaming tutor integration remains separate. Both repos private.


## 2026-10-01 — opt-in exact answer reuse

Workspace tutor checkbox can reopen matching saved reply without a model call, event or duplicate save. Exact full request/history/context and prompt-version match; same feedback exclusions and source-status checks. Dated response clearly says historical; external dataset identity/freshness is not certified. Defaults off and can return to fresh generation. Verification: 443 backend plus final four focused cases, 224 frontend, lint/types/build, two browser journeys, independent review clear. Next: local quality/latency evaluation, semantic matching and main streaming tutor integration. Both repos remain private.


## 2026-10-01 — local answer-memory diagnostic

Added local-only paired prompt evaluation with disposable DB, loopback Ollama and no hosted credentials/budget. Three cases times two conditions times three revisions (18 real local responses) recorded. Prior-ID citation issue persisted despite wording; v4 removes IDs from model input while retaining saved provenance. V4 still invents [1], so citation/teaching quality gate remains failed. Individual wrong-arithmetic and injected-instruction cases succeeded; no general quality or latency win claimed. 444 backend tests and lint/types passed; independent review clear for infrastructure, not quality acceptance. Next: final-response unsupported-citation handling and broader local evaluation before semantic expansion. Both repos remain private.


## 2026-10-01 — workspace citation disclosure

Final source-free workspace replies now disclose possible unsupported numeric citations before display/save/read-aloud, preserving raw text in metadata. Common code spans/fences/indexing are exempt. Prompt version v5 invalidates exact reuse of earlier unguarded replies. 453 backend tests, lint/types and independent code/pedagogy review passed; six recorded outputs replayed through finalizer without text loss. Heuristic limitations and underlying model-quality failures remain explicit. Next: broader provenance/quality evaluation alongside semantic candidate search; no new correctness claim or extra generation call. Both repos private.


## 2026-10-01 — semantic retrieval feasibility

Measured installed local nomic embeddings with six synthetic candidate answers and four paraphrases: batch330ms, subsequent queries15–16ms (single trials, not end-to-end). Deliberately wrong reversed formula outranked the correct answer, confirming semantic scores cannot establish truth or authorize replay. Three other top1 matches correct. Added reproducible local-only diagnostic and staged cache/filter/lifecycle design; no runtime integration yet. Lint/types and independent review clear. Next: owner-scoped derived vector cache with wipe/model invalidation, then lexical-semantic fusion; quality gates remain open. Both repos private.


## 2026-10-01 — private answer-vector cache foundation

Added learner/answer unique derived vector cache with answer fingerprint and model/format key, bounded finite vectors, owner/current-answer joins and live feedback exclusions. Delete cascade and populated two-learner export/wipe verified. Migration c16887272890 reviewed outside watched tree, copied up/down/up preserved FTS/FK, snapshot then local application. 460 backend tests, lint/types, migration checks and independent review pass. No vectors populated and no semantic runtime integration yet; next is local embedding population and scoped fusion. Both repos private; sanitized checkout has schema only, no runtime database.


## 2026-10-01 — explicit local answer indexing

Added scripts/index_answers.py bounded missing-vector population/rebuild using installed loopback Ollama and registry+tag+artifact digest cache identity. Exclusions precede limit; batches16 run outside DB transactions, log attempts and preserve completed writes on later failure. Live smoke found0eligible answers, so no embeddings fabricated. 462 backend tests plus3focused post-review regressions, lint/types pass. Review fixed skipped-write transaction leak between batches. Next: automatic post-save population and query-time scoped fusion. Both repos private.


## 2026-10-01 — workspace semantic memory connected

Literal-first lookup now fills remaining historical-context slots from scoped cached local semantic matches, with optional2sbudget/fallback. Query-only embedding, ownership/task/work filters before boundedpool, feedback/fingerprint recheck after inference, no semantic exactreplay. Completed workspace replies schedule bounded indexing in a separate session after delivery. 464 backend before reviewfix, focused semantic/memorytests afterward and lint/types pass. Review fixed tiny-vector norm failure. Local disposable smoke found paraphrase missed by literal in33ms singletrial; no generalquality/latencyclaim. Next: integration into mainstreaming tutor and broader end-to-end evaluation. Both repos private.


## Lesson historical context
Bounded literal context requires owner, skill, style and exact effective teaching contract plus unchanged source hashes. History is labeled separately from evidence. 468 backend,225 frontend,lint/build and isolated explanation-reader journey pass. Review fixed hint-level leakage. Local six-trial diagnostic shows arithmetic correction and injection resistance but remaining style/brevity errors; no broad quality or speed claim. Semantic lesson retrieval remains pending. See slices/lesson-answer-memory.md. Both repositories remain private.


## Lesson semantic history
Scoped cached local paraphrase retrieval, post-inference source checks and2soptional fallback now serve lesson turns. Keyed lessons index via separate HTTP jobs/CLI. Review fixed stale lexical matches during inference in both tutor paths.473backend/lintpass; one synthetic local lookup50msfound paraphrase missed by literal. No quality/performance gate claimed; broader evaluations and recovery/correction remain. Both repositories remain private.


## Exact replay reliability
Exact request filtering now precedes relevance limits and handles punctuation and nested Unicode/key order.476backend/lintpass; review clear. One synthetic buffered local run:13.581sinitialgeneration versus14msexactreplay with0modelcalls; changedwork regenerated. No general latency/quality claim; numeric fidelity and explicit/Socratic behavior remain open. See slices/exact-answer-lookup.md. Both repositories private.


## Typed workspace teaching choice
Explicit/Socratic mode is transmitted outside quoted history, matched by memory lookup and preserved through UI actions. Promptv6;477backend,frontend suite,lint/build,2desktop/narrow journeys pass. Model-quality gate remainsOPEN: local samples still misattribute corrected arithmetic and sometimes ignore hint-only instructions. Raw synthetic samples retained; no route change or correctness claim. See slices/workspace-teaching-mode.md. Both repositories private.


## Local feedback candidate diagnostic
Twelve pinned synthetic calls across3installedlocalmodels expose incorrect arithmetic/attribution, omitted correction and hint violations. No supported winner; no live routing change. Exact request/raw output evidence and next binding/checking plan in slices/local-feedback-candidates.md. Local/disposable boundaries reviewed; lint/typespass. Both repositories private.


## 2026-10-01 — exact current learner-answer binding

Complete bounded task answers now travel separately from run output and remain inspectable in saved detail/immediate followup. Changed-answer memory/replay excluded; Socratic start/hint sends no unsent answer.479backend/227frontend, final17backend/29frontend focusedchecks, lint/build,2desktop/narrow journeys and independent reviewpassed. Four pinnedlocalGemmatrials still contain wrong arithmetic and spurious critique: noqualitypass or routingchange. See docs/slices/exact-learner-answer.md. Next scoped checks then re-evaluation. Both repositories remainprivate.


## 2026-10-01 — local literal arithmetic feedback

Workspace feedback now includes bounded deterministic equality checks for supported submitted arithmetic, with exact fraction/decimal values and an explicit limitation: this is not a grade or validation of the formula's application. The model cannot remove the final disclosure; saved/read-aloud text retains it, and raw model text/check metadata are preserved. Hints are excluded; prompt v8 invalidates earlier replay. Review fixed ambiguous partial parsing. Final verification: 542 backend tests, 228 frontend tests, lint/types and independent re-review passed. Twelve local diagnostic calls are preserved. The final wrong-division sample was corrected, but leaked tags and a false fraction objection keep the quality gate open. No routing or mastery change. See docs/slices/workspace-arithmetic-checks.md; attribution, recovery/correction and wider queues remain.


## 2026-10-01 — browser contract regression repair

The complete GitHub journey suite exposed one stale assertion after the answer-binding change: answer-feedback.spec.ts still expected the learner's answer in execution output. Updated it to assert the exact learner_answer and empty output, retaining the feedback, audio and changed-work checks. All 39 isolated Chromium journeys now pass locally; independent review found no blockers or majors. This changes a test contract, not application behavior. Remote CI remains pending the new push.


## 2026-10-01 — quoted-feedback diagnostic

Experimental exact-answer quotation validation and seven synthetic cases per model completed. Local models still made interpretation errors; hosted comparison improved the sampled judgments but repeated a solved Socratic question. No runtime routing or learning-state change. 547 backend tests and lint/types passed; independent code/pedagogy review clear. Evidence, estimated cost and limitations: docs/slices/quoted-feedback-diagnostic.md. Earlier runtime CI passed both workflows. Both repositories remain private.


## 2026-10-01 — expanded feedback comparison

13 synthetic cases with the version2 prompt completed. Hosted sample supports narrowly scoped explicit answer feedback; local model still makes material interpretation errors despite valid quotations. No runtime integration or routing change. Lint/types, script checks, five contract tests and independent review passed. See quoted-feedback-diagnostic and planned explicit-answer-feedback slice docs for evidence, estimated cost and limits. Both repos remain private.


## 2026-10-01 — explicit formative answer checks

Connected Check/Review my answer to a separate evaluated task with exact quotations, provider disclosure, exclusive model overrides, full bounded material, saved replay and shared audio text. Other tutoring defaults unchanged. 556backend/230frontend, lint/build and desktop/narrow keyboard journeys pass, including final focused checks. Code/pedagogy review clear. 13 synthetic runtime cases recorded; model judgments remain fallible. See docs/slices/explicit-answer-feedback.md. Both repos private; no learner content/database in this checkout.


## 2026-10-01 — completed-answer save recovery

Retry saving now preserves the exact completed turn without model calls across study/workspace/follow-up/lesson/voice surfaces. Signed receipts expire after one hour or backend restart; text copy remains available. Owner/session and duplicate checks preserve provenance; partial results excluded. 561backend then6final focused,236frontend then18final focused, lint/build and two desktop/narrow keyboard journeys passed. Independent review clear. Previous sanitized CI exposed a premature follow-up click in a test; it now waits for query readiness. See docs/slices/answer-save-recovery.md for limits and remaining request-idempotency work. Both repos private.


## 2026-10-01 — durable workspace request foundation

Optional UUID Idempotency-Key on workspace tutor now claims a learner-scoped SQLite row
before inference. Same payload replays the original completed response; changed payload
conflicts, and running/interrupted claims never silently generate again. Records export/wipe
with learner data; session deletion cascades. Six regression tests, full backend568 and lint
passed; disposable snapshot migration upgrade/downgrade and independent code review clear.
UI does not send keys yet: next implement persistent retry identity, explicit new-request
choice, storage-failure handling and browser journeys. Main lesson/voice request dedup remains
separate. See docs/slices/workspace-request-recovery.md. Both repositories remain private.
Previous recovery commits041e7b6/cefa84a now have successful remote CI.


## 2026-10-02 — workspace retry controls connected

Study Tutor and Playground now send durable request UUIDs and freeze original payloads in
tab-scoped session storage. Retry previous request recovers without a second generation;
replacing unresolved work requires explicit discard. Earlier-feedback labels and typed edits
are retained. Denied storage offers explicit in-memory continuation with honest reload limits.
Full frontend241 before final fix, final focused35, lint/build and five isolated browser
journeys passed. Code review storage-denial major fixed and re-reviewed; pedagogy review clear.
See docs/slices/workspace-request-recovery.md. Saved-follow-up, lesson-stream and voice request
identities remain separate; broader content-correction, UX, materials and visual queues remain
open. Foundation commits31ef40a/89fa9f6 passed both remote CI workflows. Both repos private.


## 2026-10-02 — saved follow-up retry recovery

Saved-answer follow-ups now share durable request identities. Fingerprints include parent
answer and route plus typed question/session; owner checks precede replay. The UI freezes
parent/question, restores explicit retry after reload and retains a newly edited next draft.
Changed feedback cannot silently regenerate an old request. Full backend570/frontend243,
lint/build, seven isolated recovery journeys and required code/pedagogy reviews passed.
No paid inference, new dependency or migration. See docs/slices/followup-request-recovery.md.
Lesson-stream/voice request recovery and broader correction/UX/material/visual queues remain
open. Both repositories remain private; private snapshot refreshed before commit.


## 2026-10-02 — lesson transport recovery foundation

SSE and buffered lesson API now accept a shared UUID request identity. Original terminal meta/
done (including partial outcome) persist before delivery; replay repeats neither inference,
explained events nor checkpoint writes. Unresolved claims do not rerun. Failure copy no longer
claims nothing changed after a late persistence error. Six regression tests, full backend576,
lint/types and code/pedagogy reviews passed. No new migration, dependency or paid calls.
Browser identity/preserved partial-text integration remains next, with explicit replay metadata
and hint-evidence gating required before shipping it; see docs/slices/lesson-request-recovery.md.
Voice remains separate. Both repos private, broader project queues still open.


## Lesson browser recovery — 2026-10-02

Scoped lesson requests now survive reload with their exact retry identity, received text and
unsent draft. Explicit retry/discard controls and storage failure notices preserve choice.
Recovered metadata cannot reapply lesson hints; checkpoint hint evidence survives reload.
Question-help remains ephemeral and isolated. Backend576/frontend250 plus final hook12,
lint/types/build and three isolated browser journeys passed. Code/pedagogy review major fixed
and re-reviewed clear. See docs/slices/lesson-request-recovery.md. Voice lifecycle recovery,
question-help persistence and broader queues remain open; no personal voice gate claim.


## Voice interruption fence — 2026-10-02

Interrupt retains displayed text, suppresses queued audio/content and waits for both terminal
and acknowledgement before accepting new work. Empty transcription is a terminal path; stale
timers cannot close the next turn. Cleanup timeout closes the socket with explicit reconnect.
Persistent wording distinguishes partial display from separately saved completed replies.
Frontend254, lint/types/build and strict fake socket/microphone tests passed. Independent code
and pedagogy findings were fixed and re-reviewed clear. No live audio benchmark claim. Full
voice reload/identity recovery remains open; implementation sequence is recorded in
`docs/slices/voice-interruption-recovery.md`. Previous lesson CI passed in both repositories.


## Voice text/draft recovery — 2026-10-02

Voice panels retain bounded tab-local transcript, reply text and unsent draft, scoped by session,
skill, language and conversation. Restore stays disconnected, without audio or receipts; text
is explicitly potentially incomplete. Stop preserves work; Clear removes it and failed storage
clear keeps the panel open. Context changes dispose the previous connection. Frontend258,
lint/types/build and two isolated desktop/narrow keyboard journeys passed; zero voice sockets
opened by recovery. Required reviews clear. See docs/slices/voice-text-recovery.md. Server voice
turn identity and terminal text retrieval remain next; no full voice recovery/benchmark claim.


## Voice session exclusivity — 2026-10-02

Typed fallback and session restart now respect the previous voice task's cooperative cleanup
timeout, as do speech and barge-in. Unfinished work keeps its task/session ownership; a new
request is explicitly rejected, never silently queued. Regression reproduced before fix.
Backend579, focused voice tests and lint/types passed; required reviews clear. See
`docs/slices/voice-session-exclusivity.md`. This is per-connection admission safety; provider-
resistant teardown and durable voice identities/recovery remain open. No paid calls or live
microphone work. Previous interruption CI passed in both repositories.


## Typed voice request correlation — 2026-10-02

Negotiated typed-v1 UUIDs now follow typed voice metadata/tokens/audio/errors/done through
response and speaker tasks. Client ignores late content from another request; reconnect resets
negotiation before startup errors. Legacy clients and microphone turns remain compatible.
Backend580/frontend260, lint/types/build and fake-provider WebSocket regressions passed; required
reviews clear. Correlation only, not idempotency or durable replay. See voice-request-identities
slice; microphone identities, terminal lookup and provider-resistant teardown remain open.


## Microphone capture identity — 2026-10-02

Negotiated utterance-v1 adds a capture UUID before explicit Talk. Processing closes the capture
and browser microphone; late PCM frames or end controls cannot start another STT call. All
speech response/audio events retain the capture ID and stale client messages are ignored.
Typed turns invalidate old capture buffers. Legacy protocol remains supported. Backend581,
frontend261, lint/types/build and required reviews passed with fakes only. See
`docs/slices/voice-capture-identities.md`. No durable voice replay or personal benchmark claim;
control identities, terminal lookup, unresolved UX and provider-resistant teardown remain open.


## Voice interruption controls — 2026-10-02

Current request identity now survives capture closure. Stale/missing interrupts cannot affect
a newer identified request; matching acknowledgements carry identity and the client still waits
for terminal completion. Connection-wide Stop and legacy behavior remain intact. Backend582,
frontend262, lint/types/build and required reviews passed with synthetic tests. See
voice-control-identities slice. Durable terminal lookup, unresolved recovery and resistant-provider
teardown remain open. Correlation is not an exactly-once or full-recovery claim.


## Durable voice terminal recovery — 2026-10-02

Identified voice requests now claim the existing ledger before LLM/TTS work and persist terminal
text/receipt before delivery. Matching requests replay text without inference/audio/evidence writes;
changed payloads conflict and unresolved claims cannot regenerate. Owned GET lookup distinguishes
missing, unresolved, completed and partial. Backend587/frontend262, generated types, lint/build and
required reviews passed. Claim-time interruption race fixed and regression-tested. See
`docs/slices/voice-terminal-recovery.md`. Pending UUID browser recovery and provider-resistant
teardown remain open; STT precedes this claim and is not deduplicated. Personal voice gate open.


## Area journey initialization — 2026-10-02

CI run 36942008712 failed because the area journey read the catalog before the initialization
POST completed. The test now waits for that specific response, asserts success, and verifies the
expected area exists. The isolated fresh-sandbox journey passes; code review found no blockers
or majors. This changes test synchronization only, not area generation or learner behavior.


## Browser voice result recovery — 2026-10-02

Pending voice UUIDs persist before identified text/capture admission. Explicit read-only recovery
returns missing/unresolved/partial/completed states without sending, microphone or playback.
Recovered terminal text survives dismiss/reload alongside the next draft. Storage denial has an
explicit page-only choice; stale responses and 15-second lookup deadlines are tested. Frontend273,
lint/types/build, two isolated desktop/narrow keyboard journeys and required reviews passed. See
`docs/slices/voice-browser-result-recovery.md`. Previous CI passed in both repos (36943227815,
36943244831). Provider-resistant teardown and personal voice benchmark remain open.


## Voice shutdown ownership — 2026-10-02

WebSocket teardown closes transport then shields response/speaker cleanup before exiting its
explicit database context. Owner cancellation is propagated only after child cleanup; a speaker
created after shutdown begins is included. Backend590, lint/types, sanitized voice24 and code
review passed. See `docs/slices/voice-shutdown-ownership.md`. Interactive timeout stays 15 seconds;
a genuinely stuck provider can delay final shutdown. No forced cancellation inside SQLite and no
exactly-once guarantee. Personal recordings benchmark and broader learning queues remain open.


## Saved-answer follow-up history — 2026-10-02

Saved answers now expose their direct later replies through an owner-scoped parent filter and
lazy history panel. Search/pagination retain that filter; hidden/reported replies are history,
not verified replacements. No inference or evidence writes. Backend591/frontend275, lint/types,
production build, two desktop/narrow keyboard journeys and required reviews passed; sanitized
focused backend4/frontend10 passed. See `docs/slices/answer-lineage-history.md`. Explicit proposed
correction and preferred-replacement workflow remains next; original answers remain immutable.


## Explicit correction requests — 2026-10-02

Saved-answer follow-ups now have an explicit correction purpose, editable template with draft
protection, reload/retry persistence and purpose-sensitive request identity. Proposals are labeled
in the conversation and reopened history. Saved reports remain untrusted evidence to examine;
original answers and feedback are never rewritten. Backend592/frontend276, lint/types/build,
two desktop/narrow browser journeys and required reviews passed; sanitized backend5/frontend10.
See `docs/slices/answer-correction-requests.md`. No paid/live model quality claim. Learner-reviewed
preferred replacement, reversible eligibility and selector parity are next.


## Shared answer eligibility — 2026-10-02

The five exclusion queries now share db/answer_eligibility.py: suggestions, workspace lexical/exact,
lesson memory, vector loading and indexing. Existing owner/hidden/incorrect/outdated semantics
are unchanged; history remains readable. Backend592, lint/types, focused24 in both checkouts and
code review passed. See `docs/slices/answer-eligibility-policy.md`. This prepares consistent
replacement exclusion; replacement choice/undo/CAS and learner UI are still outstanding.


## Reviewed preferred corrections — 2026-10-02

Explicit reviewed choice and undo now persist in learner-scoped tutor_answer_replacement. Only
owned direct correction children qualify; CAS/repeat-safe writes preserve originals and feedback.
Shared eligibility excludes replaced originals across all automatic reuse paths. Browser controls
have bounded requests and late-response protection; preference is never verification/mastery.
Migration9c2187eaf014 passed on a disposable snapshot before publication; live auto-migration and
foreign keys verified. Backend595/frontend279, lint/types/build, two desktop/narrow journeys and
required reviews passed; sanitized backend45/UI3 passed. See answer-preferred-replacement slice.
Next: remaining representation/assessment links and broader real-material quality/latency checks;
material coverage, UX, visual/authoring/resource and personal-voice queues remain open.


## Representation provenance — 2026-10-02

Cached alternative explanations retain supplied-source metadata, citation flags and text hashes.
Legacy entries explicitly report unknown provenance; current passage views are not historical
verification. Backend595/frontend281, focusedAPI4, lint/types/build, two isolated desktop/narrow
journeys and required reviews passed. Browser review fixed duplicate source/audio sibling keys.
See docs/slices/representation-provenance.md. Durable representation answer history and assessment
linkage remain next; this is a prerequisite, not completion of saved-answer path coverage.


## Representation answer history — 2026-10-02

Delivered alternative explanations now enter searchable immutable answer history. Cache invalidation
cannot delete them; cache hits reuse the learner/session/representation entry. Save failures retain
text and signed save-only recovery. UI includes saved link and distinct history filter. Full backend599,
then focused5 including concurrent cached delivery; frontend282, lint/types/build, two desktop/narrow
journeys and required reviews passed. See docs/slices/representation-answer-history.md. Assessment
feedback linkage is next; fresh-generation request deduplication and broader quality remain open.


## Assessment session ownership — 2026-10-02

Both assessment routes now require the current learner to own the supplied session before next-item
generation or grading. Regression reproduced foreign-session 200 responses, then verified equal
404 responses and no attempt/evidence/memory/event/model/history changes after rejection. Backend602,
lint/types, sanitized focused6 and code review passed. See docs/slices/assessment-session-ownership.md.
Next: saved assessment feedback linkage without regrading or duplicate learning evidence.


Assessment ownership follow-up: challenge start/submit now have the same ownership guard. Two pre-fix regressions reproduced; focused12 and lint/types passed, code review clear. All four grading entry routes identified in this audit are guarded. Saved assessment feedback remains next.


## Saved assessment feedback — 2026-10-02

Shared Grader now saves completed feedback and original visible question/answer/result, linked to
the attempt. All four result surfaces expose saved history/retry. History is searchable with readable
past grading details; personal feedback is excluded from default suggestions and automatic reuse.
Recovering a failed save never regrades or adds evidence/reviews. Full backend608/frontend282, focused
backend5/UI14, lint/types/build, two desktop/narrow journeys and required reviews passed. See
docs/slices/assessment-feedback-history.md. No old-attempt backfill or grading-request idempotency
claim; broader quality, material coverage and UX queues remain open.


## Assessment request recovery foundation — 2026-10-02

Assessment/challenge accept shared namespaced UUID request claims; equal completed retries replay,
changed work conflicts, unresolved requests never grade again automatically. Owned/session-scoped
GET lookup reports not_found/unresolved/completed without evidence writes. Backend613, focused4
(including fresh connection), lint/types and code review passed. See assessment-request-recovery slice.
Next: browser UUID/frozen payload persistence and explicit result recovery on all four assessment
surfaces. Legacy unkeyed clients remain unprotected; atomic whole-grade writes/R3 are still open.


## Browser assessment recovery — 2026-10-02

All four assessment surfaces now persist a UUID and frozen submission before sending, then offer
read-only result lookup after interruption/reload. Only an explicit not-found retry sends the same
identity and original body. Historical feedback never silently replaces edited work. Requests are
bounded and stale completions fenced. Storage denial/damage has an acknowledged page-memory fallback;
reloading loses memory-only recovery. No automatic grading retry or mastery from browser state.
Verified: frontend293, desktop/narrow lost-response journeys2, types/build/lint and required code and
pedagogy reviews. See docs/slices/assessment-browser-recovery.md. Next: atomic whole-grade writes and
review-rating idempotency; content-version conflict protection and broader quality/UX gates remain open.


## Atomic grading writes — 2026-10-03

R3/F04 partial-save defect reproduced before the fix. Shared Grader now owns one learning transaction
for attempts, events, evidence, FSRS, competency and hint checkpoint reset, after model accounting.
Failure/cancellation rolls all learning writes back; helper defaults preserve other callers. Full
backend629, final expanded failure boundaries18, lint/types and required code/pedagogy reviews passed.
See docs/slices/atomic-grading-writes.md. Request completion after learning commit remains a recovery
gap; review-rating idempotency and content-version guards are still open. No migration/UI change.


## Committed assessment outcome recovery — 2026-10-03

R3/F04 post-commit recovery gap is closed for newly keyed grading requests: original result plus
versioned private history snapshot commit with learning state. Read-only lookup/replay links saved
history or issues a new save-only receipt after restart; it never grades again. Historical outcome
labels no longer imply current mastery/review timing. Backend636, UI16, desktop/narrow journeys2,
lint/types/build and required reviews passed. See docs/slices/atomic-assessment-outcome.md.
Next: review-rating ownership/idempotency. Pre-commit unresolved requests, legacy unkeyed callers
and content-version conflicts remain limited; broad quality/material/UX queues remain open.


## Review request recovery foundation — 2026-10-03

Review due/rating now check session ownership; keyed ratings bind the frozen payload to a durable claim.
FSRS card/log, reviewed event and completed result commit atomically after acquiring a short write lock.
Lookup is read-only. Full backend643, final request tests8, generated API types, lint/types and required
reviews passed. See docs/slices/review-request-recovery.md. Next: browser review identity persistence,
explicit lookup/retry and current-queue reconciliation. Until then unkeyed browser retries are not
protected; R3 stays partial. No live learner mutation or paid model call during verification.


## Browser review recovery — 2026-10-03

Review and vocabulary ratings now persist a frozen UUID/body before sending, recover by explicit
read-only lookup, and only resend a confirmed missing request with the original identity. Completed
intent remains until the queue checkpoint is stored; storage failures expose an acknowledged page-memory
fallback. Stable vocabulary IDs replace positional progress. Confirmed recovery clears only that
card's help and resets confidence/timing. Full frontend305, desktop/narrow journeys2, lint and production
build passed; code and pedagogy reviews cleared. See docs/slices/browser-review-recovery.md.
R3 remains partial: content-version guards, legacy callers and pre-commit unresolved recovery remain open.
Next priority per owner: reconcile the new UX research and simplify the Programs learning journey.


## Project-study orientation and UX research — 2026-10-03

Owner reported continued UI confusion and supplied two research reports. Merged useful methods into
docs/UX-RESEARCH-INTEGRATION.md and docs/UI-INVENTORY.md; updated shared UX skill guidance.
Programs now leads with current step/explanation, collapses course switching, remembers selected
course/step, and distinguishes task starter from full-course notebook with explicit return.
Frontend309, eight isolated browser journeys, main-content axe/320px/200%text, lint/build and code/
pedagogy reviews passed. See docs/slices/project-study-orientation.md. No backend/model change.
Next UX26-04: clarify tutor conversation choices without hiding provider disclosure or changing
Socratic defaults; then UX26-05/06/08 shell/audio/shared controls. Owner comprehension remains OPEN.
Both repositories remain PRIVATE. Broader material, visual, authoring and voice benchmark queues remain.


## Tutor choices — 2026-10-03

UX26-04 delivered: explanation/hint lead, irrelevant empty-answer review removed, guided questioning
is an explicit optional disclosure with active approach visible and Explain instead directly available.
Saved reuse is secondary with on/off shown. Provider/data disclosure, prompt/routing, follow-up and
recovery remain unchanged. Undefined tutor border/surface classes now use existing tokens.
Frontend310, focused26, nine desktop/narrow browser journeys, lint/build and both reviews cleared.
See docs/slices/study-tutor-choices.md. Next UX26-05 shell/status, then audio and shared controls.
Owner comprehension and broad queue remain open; both publication repositories remain PRIVATE.


## Shell orientation — 2026-10-03

UX26-05 implemented: route-specific document titles, exact current-page navigation, explicit Home,
keyboard skip/main focus, in-flow tools including Materials/Lesson drafts, consistent Project study
name and unknown-page return. Browser-only session ID no longer asserts running; Resume/manage
links Home for the existing server check. Full frontend313/81 files, focused3, desktop/narrow shell
journeys2 plus project orientation2, scoped header axe/200% text/reflow, lint/build and reviews passed.
See docs/slices/shell-orientation.md. Next UX26-06 audio status/controls and UX26-08 shared controls.
Owner comprehension and manual full accessibility gates remain open. No learner lifecycle/model change.


## Read-aloud status — 2026-10-03

UX26-06 first slice: preparation, inter-passage waiting, playback, completion and explicit stop
are visible; muted/zero-volume notices are outside collapsed settings. Completion releases playback.
Frontend316, focused6, two isolated audio browser journeys, lint/build and both reviews passed.
See docs/slices/read-aloud-status.md. Pause/resume, cross-surface coordination, device audibility
and owner comprehension remain open. Both publication repositories remain private.


## Read-aloud pause — 2026-10-03

UX26-06: requested speech now offers Pause/Resume without regenerating audio. Arriving passages
remain queued while paused. Stop remains available during pending context operations; old operations
cannot change replacement playback. Frontend319, focused9, browser2, lint/build and both reviews passed.
See docs/slices/read-aloud-pause.md. Cross-surface coordination and real-device/owner gates remain open.


## Requested-reading coordination — 2026-10-03

Starting another ReadAloud stops the previous reading, including preparation or pause, with a reason.
Stale releases cannot clear a newer owner. Full frontend322, focused11, browser audio2, lint/build and
reviews passed. See docs/slices/read-aloud-coordination.md. Scope is one tab's requested readings;
voice-conversation/media coordination and global transport controls remain outstanding.


## Shared requested-reading transport — 2026-10-03

Every Audio controls panel now exposes current requested-reading status and Pause/Resume/Stop for the
same player. Controls clear on release and stale owners cannot replace them. Frontend324, focused13,
browser2, lint/build and reviews passed. See docs/slices/shared-reading-controls.md. Coordination with
voice conversations/other media and physical-output/owner gates remain open.


## Local diagnostic provenance — 2026-10-03

Local feedback diagnostic report v2 names runtime message-builder/version/intent, current feedback
fragment hash via runtime loader, and diagnostic versus production task. It explicitly disclaims
full respond/routing/semantic-quality coverage. Inference/defaults unchanged; focused11, Ruff/format
and independent reviews passed. See docs/slices/local-feedback-diagnostic-provenance.md. Next: bounded
full-runtime local evaluation before considering any hosted-route replacement. No paid calls.


## Home topic readiness — 2026-10-03

Home identifies the selected new-session topic, waits for selection saves and lesson lookup, and
offers Review and activate a lesson for confirmed empty topics. Existing session resume remains
separate; no unrelated lesson fallback or automatic activation. Home9/full frontend328, browser4,
lint/build and independent code/pedagogy reviews passed. See docs/slices/home-topic-start.md.
Catalogue performance and owner usability confirmation remain separate open work.


## Area catalogue performance — 2026-10-03

Catalogue matching now groups metadata and compiles expressions once, off the event loop with plain
immutable snapshots. Exact membership parity confirmed on the local corpus; aggregation ~20s to
0.64s. Live endpoint after restart 0.926s with concurrent health/skills responsive. Independent code
and pedagogy reviews clear. See docs/slices/area-catalogue-performance.md for limits and checks.


## Browser assessment isolation — 2026-10-03

Fresh sandbox-only deterministic assessment fixtures remove shared-attempt ordering failures.
All 65 integrated browser journeys passed locally; code review clear. Linux CI still requires
verification, including a separately investigated narrow-text overflow. No production behavior
change. See docs/slices/browser-assessment-isolation.md.


## Actual local tutor diagnostic — 2026-10-03

Disposable runtime diagnostic now exercises actual respond/persistence with hosted providers disabled.
21 focused tests cover mechanics. First local four-case run: three generations, exact reuse zero calls
(11ms), revised answer regenerated; semantic review three passes and one partial literal-criterion
pass (decimal corrected, percentage left for learner). No routing change or broad quality claim.
See docs/slices/local-runtime-feedback-diagnostic.md; realistic/repeated quality evaluation remains open.


## Project-study reflow — 2026-10-03

Explicit single grid column fixes reproduced narrow-screen overflow with 200% text and increased
letter spacing without clipping or shrinking content. Desktop/narrow integration journeys and
independent reviews pass. Linux CI confirmation remains pending. See docs/slices/project-study-reflow.md.


## Bounded material import verification — 2026-10-03

Privately captured two additional lesson texts/transcripts and one external PDF, with source
provenance retained only in the private archive. All three imports succeeded; all60 new nonduplicate
chunks matched search-index text. One external article remains unresolved after an HTTP error.
Acquisition/ingestion is not complete-course coverage or learner completion; curriculum activation
was not changed. The earlier exercise capture is also preserved in the private archive.


## Nested lesson reflow — 2026-10-03

Linux CI confirmed64/65 journeys passing: original200% reflow passed but spacing stress exposed
a nested lesson-grid minimum. Inner column now shrinks, phase labels wrap/grow, and bookmark
selector fits. Existing actions/semantics remain. Independent reviews clear; Linux rerun pending.
See docs/slices/project-study-reflow.md.


## Private external-resource reconciliation — 2026-10-03

A private read-only ledger now joins source provenance, latest acquisition statuses, historical
files and SQLite evidence. Conservative URL normalization preserves meaningful query/fragment data;
credential review is required before storing future outputs. Current artifact reviewed without
credential evidence. Three historical rate-limited downloads recovered; their ingestion is separate.
No index/completeness claim. Source identifiers, script and detailed report remain private only.


## Reference recovery and index checks — 2026-10-03

A recovered notebook resolves to nine existing canonical chunks, all verified in local search;
no notebook execution or dependency installation. Another lesson/transcript and two repaired
external PDF references imported with197/197 indexed texts verified. Original failed URLs and
replacement provenance remain private; one additional reference timed out. Historical documents
remain historical sources, not assertions of current policy. No curriculum activation changed.


## Linux CI verification — 2026-10-03

Both complete workflows succeeded after the nested reflow fix: archive eaafd63/run37117683380 and
sanitized6adeabc/run37117696816. This includes all65 browser journeys plus backend, frontend and
migration jobs, with the sanitized publication guard. Owner usability/device checks remain open.


## Voice/reading coordination — 2026-10-03

Explicit voiceTalk/voiceSend and requested readings share identity-safe in-tab ownership. Replacement
stops capture/queued audio and preserves text; Connect/text-only requests do not displace readings.
Shared controls name voice activity and Stop. Full frontend333, browser5, independent code/pedagogy
reviews passed. See docs/slices/voice-reading-coordination.md. Media/visualizer/ambient/test-tone and
physical audio/owner gates remain open; no model or backend changes.


## Full local index parity — 2026-10-03

Read-only audit matched185232 expected latest canonical chunks with185232 index points, with no
missing, extra, text, identity, document or ordinal mismatch; final counts stable. Duplicates and
older versions correctly excluded. Audit tool/report remain private. Environment proxies disabled,
redirects forbidden; independent review clear after transport fix. No inference/reindex performed.
Vector quality, all provenance fields and guarantees against concurrent replacement remain outside
scope. This is storage parity, not retrieval relevance or full course coverage.


## Home topic activation clarity — 2026-10-03

Topic choices now show activated lesson counts, distinguishing imported sources/drafts from lessons
that can be considered by the planner. Empty selections keep the topic and lead to draft review;
activated-but-unavailable selections lead to the skill map. Learning areas offer a direct Review
prepared draft shortcut, skipping interrupted drafts, with activation still explicit. Draft mutations
refresh the area catalogue. The catalogue adds one node query, no per-area mastery lookups.

Verified: backend3, integrated frontend19 in both variants, earlier full frontend334 for the Areas
delta, isolated browser1 for ready→empty→ready and correct-topic start, TypeScript/lint/build passed.
Live backend restarted and Home/read-only draft shortcut checked. No learner preference, activation
or session changed in live data. Source/pedagogy review findings resolved. See
docs/slices/home-area-activation-counts.md. Other queued work remains separate and unfinished.


## Listening clip coordination — 2026-10-03

Listening clips join reading and voice in the shared in-tab audio owner. Starting another activity
pauses the clip, explains why and retains position; resuming is explicit. Global clip controls now
pause/resume/stop; volume/rate keep existing preferences. Late play promises cannot revive replaced
audio or interrupt a newer play, and paused seeks do not inflate exposure. Integrated frontend338,
two isolated coexistence browser journeys, TypeScript/lint/build passed; sanitized focused20 plus
TypeScript passed. Independent code/pedagogy reviews clear. No real audio/model/microphone or live
learning-state changes in tests. Physical Bluetooth audibility and visualizer/ambient/test-tone
coordination remain open. See docs/slices/listening-audio-coordination.md.


## Additional material imports — 2026-10-03

Two transcript archives and two captured lesson pages are ingested:24 documents,51 new indexed
chunks and one stored duplicate resolving to an existing canonical chunk. A bounded read-only audit
verified all52 distinct canonical targets, text, identity, ordinal, latest version and provenance.
This establishes storage/index availability for this batch, not complete course coverage, retrieval
quality or notebook execution. Raw captures, archives, acquisition reports and detailed verification
remain in the private archive only. No activation or assessment/attendance actions were performed.


## Realistic local notebook feedback evidence — 2026-10-03

The opt-in notebook diagnostic adds8 synthetic exact-work cases, fixture fingerprints and separate
semantic criteria; existing basic cases remain unchanged. Tests23 passed in both variants. Two real
local candidates evaluated: Llama8B2pass/1partial/5semanticfailures; Gemma12B3pass/2partial/1semantic
failure/2runtimefailures. Literal output validation did not guarantee mathematical correctness.
No production routing change; neither candidate establishes the broad notebook feedback quality
gate. Raw evaluation evidence stays private. See docs/slices/local-notebook-feedback-fixtures.md.


## Home narrow-screen regression — 2026-10-03

CI on the previous Home counts change caught selector intrinsic-width overflow at390px; all other66
journeys passed. Home now uses a zero-minimum grid track and bounded native selectors/shrinkable
labels. No overflow hiding. Seven targeted browser journeys pass, including loaded long-label
regressions at320/390 and saved-session journeys at390/800/1280. Home10 unit tests and TypeScript
pass; this corrects the reported CI failure, with next full remote workflow still to run.

Next audio slices remain visualizer audible monitoring (silent analysis stays independent), output
test-tone ownership and ambient sound ownership. Preserve explicit start/resume, identity-safe late
promises and honest Stop sound semantics. Physical headphone audibility remains an owner check.

## 2026-10-04 — UX phase 1 and pause/end clarity

Added the Phase 1 product inventory and adversarial report under docs/ux. The report ranks ten findings and records evidence limits for all 25 scenarios. Corrected only AU-01: explicit Pause and return Home preserves the active checkpoint; End session retains termination; late transition responses cannot navigate away after pause. No learning kernel, routing, grading or scheduling changes.

Verification in the original checkout: baseline browser24; first post-change regression15; final pause suite9 (corrected due-card fixture); focused unit23; lint/type/build passed; desktop/narrow screenshots and keyboard checked. No claim of real-model remediation quality, elapsed-time suspension or universal draft persistence. Next incomplete design phase is Phase2; remaining findings and coverage gaps are in the report. Both repository variants remain private.

## 2026-10-04 — Phase 2 running UX audit

Added docs/ux/UX-AUDIT.md, sanitized structural evidence and opt-in frontend/e2e/ux-audit.spec.ts. Inspected 17 route entry states at 390/800/1280/1920px, five HTTP503 states and a real local tutor session. Nine collection probes completed (not accessibility passes); 16 existing browser journeys and seven VoicePanel unit tests passed; ESLint passed. Screenshots inspected. Independent source/pedagogy reviews found no major overclaim. No production application or learning-logic changes.

Findings: loading/empty states conceal failed reads; Models overflows on narrow screens; heading/ARIA issues; one detailed model response omitted requested content despite completion wording. Two incorrect answers raised displayed mastery 0→10→21%; read-only evidence and the recall/retrievability blend are documented, not silently changed. Local model calls had zero hosted cost. Full screen-reader, physical audio, delayed human re-entry and semantic generalization remain open. Next is Phase 3 heuristic review.

## 2026-10-04 — Phase 3 heuristic review

Added docs/ux/HEURISTIC-REVIEW.md: 14 severity-sorted open findings, original evidence crosswalk, Nielsen/WCAG mappings, closed AU-01 boundaries, unresolved hypotheses, candidate file/risk/test scopes. Rechecked relevant source and primary guidance; local document links and diff whitespace validated. No new browser run or production code change is claimed. The mastery observation is serious but does not establish an algorithm defect or authorize a formula change. Next is Phase 4 persona testing, preserving human comprehension, physical audio and delayed re-entry as open gates.

## 2026-10-04 — Phase 4 persona walkthrough

Added five-profile docs/ux/LEARNER-PERSONA-TESTS.md, opt-in learner-persona-audit.spec.ts and desktop/narrow evidence. Initial combined 14 browser tests passed; tightened evidence capture to wait for refreshed teach-phase status, then final two probes passed. Focused ESLint and screenshot review completed. Same-context draft survives pause/reload; fresh context retains server checkpoint but not unsent draft. Bookmarks do not advance or award mastery. Initial combined run exposed a real adaptation proposal with raw setting key; acceptance effects remain untested. Narrow capture flags Park overlap and below-fold explanation action for later layout verification. No production code changes; no human or learning-outcome pass claimed. Next: Phase 5 information architecture.

## 2026-10-04 — Phase 5 information architecture

Added docs/ux/UX-ARCHITECTURE.md. Reconciled all 19 explicit route entries including detail and unknown-path handling; defined task groups, content hierarchy, always-reachable help/pause/audio/status and transition safeguards. No routes, features, learning logic or dependencies changed. Document links and publication sanitation checked; prior runtime evidence supports the proposal but does not validate proposed labels with users. Next is Phase 6, preserving current tokens/primitives rather than replacing them.

## 2026-10-04 — Phase 6 design-system specification

Added docs/design/DESIGN-SYSTEM.md and token-contrast.json. Inspected existing CSS and four primitives; computed20 light/dark opaque token pairs, checked primary accessibility guidance and local links. Sampled text pairs clear4.5:1; line/card is1.36/1.39 and cannot alone establish a required control boundary. This is not rendered conformance certification. Defined typography/spacing/state/component rules and missing semantic roles without production CSS or learning changes. Next: Phase7 isolated visual directions, no new component library.

## 2026-10-04 — Phase 7 isolated visual directions

Added design-experiments/ux-directions HTML and rationale, standalone design Playwright config/probes and screenshots. Three directions share one fixture, script and IA; no database/network/model calls or production replacements. Initial6 checks and final9 checks passed, focused ESLint and script syntax pass; desktop/320px images reviewed. Explicit help now focuses the updated heading and navigation preview reflects current state. Narrow layouts remain long. Dark mode, real audio/streaming/persistence and human comprehension remain outside prototype verification. Next is Phase8 scoring/recommendation.

## 2026-10-04 — Phase 8 direction comparison

Added docs/design/DESIGN-DECISION.md and nine initial-layout measurements; extended existing design probes without changing prototypes or production. Nine tests and focused ESLint passed. Weighted matrix arithmetic checked: A3.75/B3.50/C3.35; recommendation is sensitive to judgment changes, not measured learning efficacy. Quiet Workspace recommended for reading while retaining wide task surfaces. Below-fold help, human comprehension, themes/zoom and real state integration remain acceptance gates. Next: Phase 9 implementation plan.

## 2026-10-04 — Phase 9 implementation plan

Added docs/ux/IMPLEMENTATION-PLAN.md with bounded stage/slice file scopes, risks, tests, integrated acceptance matrix and original-phase mapping. Rechecked current component/test paths and document links. No production code, learning logic or new runtime test result. Next concrete slice: Phase 10/Stage 1a control-boundary and inline-code tokens, using existing CSS/Textarea with measured rendering. Navigation, mastery and recovery changes remain separate; full redesign acceptance stays open.

## 2026-10-04 — Phase10 Stage1a production tokens

Reproduced faint shared Textarea boundaries and unreadable system-dark inline code before editing. Added control/code semantic tokens to existing CSS and changed shared Textarea border only. Removed dark code selector specificity conflict, retaining transparent pre/code background.19 browser and10 unit tests passed; lint/types/build pass, existing bundle/spectrogram/canvas-environment warnings remain. Before/after contrast JSON and inspected screenshots in docs/design/evidence/phase10a. Values/callbacks/learning logic unchanged; other native fields and Park overlap remain. See docs/slices/design-control-code-tokens.md.

## 2026-10-04 — Phase10 Stage1b heading adoption

Corrected reproduced Preferences page heading through optional CardTitle heading level, preserving h2 default and appearance. Added loading-state heading without changing its existing error behavior. Two baseline checks failed for missing h1; final five browser and fourteen unit checks pass; lint/types/build pass with known warnings. Narrow before/after screenshot hashes identical; desktop/narrow visually inspected. No learning or preference mutation changes. Next: separate Preferences failed-read recovery slice (Stage2a).

## 2026-10-04 — Stage2a Preferences read recovery

Reproduced503 reads masking failure as loading. Added initial/stale-data recovery UI, existing15s bounded read and explicit retry; shared read cancellation before saving prevents late snapshots replacing saved preferences. Five browser checks, sixteen existing plus two new unit tests pass; lint/types/build pass. Screenshots inspected; exact fixture save values and keyboard retry verified. Shared-query deadline applies to other consumers; no backend or learning changes. See docs/slices/preferences-read-recovery.md. Next: separate Map read recovery.

## Map recovery and revised navigation priority — 2026-10-04

Map now has bounded reads, Retry/Home and retained cached map on refresh errors. Two unit/two browser checks, lint/types/build and read-only review pass. Park overlap remains. See docs/slices/map-read-recovery.md. New owner workspace proposal is reconciled in docs/ux/CONTEXT-WORKSPACE-PLAN.md: inventory context contracts before C1 shell changes; preserve all capabilities and learning state.

## C0 context inventory — 2026-10-04

Mapped every current route to the proposed navigation; inspected server/session, browser work and tutor target boundaries.23 browser and7 unit baseline checks pass. No application changes. Areas URL selection, Playground activity return, unsaved recap/editor state and persistent companion target remain explicit gaps. Next C1 is shell-only; see docs/ux/CONTEXT-INVENTORY.md.

## C1 grouped navigation — 2026-10-04

Home/Projects plus named Learn/Explore/Library/Tools/Manage groups preserve destinations and state.25 browser/four unit checks, lint/types/build and read-only review pass. See docs/slices/grouped-navigation.md. Park still obstructs expanded navigation at narrow200% text; correct that before C2. No learning logic or model changes.

## Park obstruction correction — 2026-10-04

Capture and status moved into header flow; dialog scrolls within viewport. Six unit/six relevant browser checks and lint/types/build pass; independent review clear. No learning changes. Header access replaces viewport-floating access. Preferences200% overflow remains separate. See docs/slices/parking-header.md. Next C2 browse-area context.

## C2a and uploaded design assessment — 2026-10-04

Area/draft choices now survive URL history and refresh; same-route history preserves unsaved editors. Five unit/three browser checks and lint/types/build pass. Normalized-save review issue fixed without overwriting newer input. Full-route draft retention and global browse context remain. See docs/slices/area-location.md. Uploaded design patterns assessed/merged in docs/design/UPLOADED-DESIGN-RECONCILIATION.md; no bundled runtime, font or skill installed.

## Browsing context and design authority — 2026-10-04

Header Browse area uses independent tab-local history and existing URLs, with explicit same-area Open.11 unit/seven targeted browser checks and lint/types/build pass. No learning-state writes. See docs/slices/browse-area-context.md. Owner explicitly made uploaded package the design system; exact canonical tokens and hashes are in docs/design/source. Earlier prototype/defer visual language is superseded. Next implement its visual foundation, documenting real accessibility/state conflicts.

## 2026-10-04 — Uploaded design palette

Adopted canonical existing color roles and 2px focus styling. Eight theme/width browser cases, lint/types/build passed in original checkout. Visual inspection of desktop light and narrow dark completed; learning logic unchanged. See docs/slices/design-palette-adoption.md. Additional owner navigation document is authoritative alongside visual/component package. Sanitized checkout also passed all eight browser cases. Paired commits/pushes follow; both variants remain private.

## 2026-10-04 — Shared button design

See docs/slices/design-buttons.md. Stronger control boundaries, explicit disabled/hover palette and wrapping-safe minimum heights; eight browser cases and lint/types/build pass. No learning behavior changed. Full shell and typography remain outstanding.

## 2026-10-04 — Shared panel design

Cards now follow supplied radius/flat surfaces, optional themed lift for Home resume, and separate panel/page heading tokens. Twelve browser cases passed in each checkout; original lint/types/build passed. See docs/slices/design-panels.md. Typography and contextual shell remain unfinished.

## 2026-10-04 — Desktop rail

Existing navigation is now separate from desktop workspace; narrow in-flow navigation retained. Ten browser checks and four unit checks pass; lint/types/build pass. See docs/slices/desktop-navigation-rail.md. Compact mobile navigation and contextual shell remain outstanding.

## 2026-10-04 — Collapsible mobile navigation

Menu starts closed on narrow screens, names current page, closes on route change/Escape, and recovers visible keyboard focus when resized. All destinations preserved. Final original 24 browser/four shell unit checks and lint/types/build pass. See docs/slices/mobile-navigation.md. Full mobile bottom navigation, compact header and persistent tutor remain open.

## 2026-10-04 — Header audio controls

Idle header audio is shorter; active status and Stop/pause are visible with settings closed. Stop restores focus. Seven unit tests, audio/parking browser checks and lint/types/build pass. See docs/slices/compact-header-audio.md. Local speech routing unchanged; physical output and broader header composition remain open.

## 2026-10-04 — Inline Work alongside

Session now offers optional quiet work panel without unmounting the lesson or losing the current question draft. Existing standalone route preserved; no automatic sound or learning writes. Three browser cases, twelve unit tests and lint/types/build pass; see docs/slices/inline-alongside.md. Broader C3 and persistent tutor remain open.

## 2026-10-04 — Playground selection recovery

Selected workspace now survives URL history/reload with its existing saved code. Invalid target feedback is explicit; no model/learning writes. Six unit and two browser cases plus lint/types/build pass. See docs/slices/playground-location.md and contextual-tools-contract.md; lesson-context transfer remains unimplemented.

## 2026-10-04 — Lesson-linked experiment

Optional lesson-to-playground entry now isolates code/chat/question drafts and returns to the current lesson. Origin checked for fresh/retry sends, late checks suppressed, original retry identity retained. 17 unit tests and lint/types/build pass; browser payload/round-trip checks cover desktop/narrow. See docs/slices/lesson-experiment.md for evidence and remaining C3 scope.
