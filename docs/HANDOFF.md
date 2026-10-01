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
