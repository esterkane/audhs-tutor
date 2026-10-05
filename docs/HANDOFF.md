# Local operational notes

## 2026-10-05 — Correct saved assessment follow-up context

Saved-answer follow-ups now receive immutable displayed answer text instead of mistaking MCQ indices for learner answers. Raw parent preserved; absent labels remain explicitly unavailable.16 tests, Ruff/mypy and independent review pass; two local synthetic before/after examples support the fix, not general accuracy. No UI or grading change. See docs/slices/assessment-followup-context.md for the next in-session dialogue/streaming boundary.


## 2026-10-05 — Help after checked feedback

Reproduced disappearing question help after grading. Added optional concept explanation beside completed feedback, without another assessment or post-grade hint evidence.12 tests, lint/types/build and desktop-correct/narrow-incorrect keyboard browser journeys passed; review clear. Exact mistake-specific dialogue remains open pending immutable answer context. See docs/ux/DAILY-LEARNING-ACCEPTANCE.md DL-03. Prior CI backend/frontend/migrations/publication now pass; browser job still running at inspection.


## 2026-10-05 — Repair CI contract drift

Test-only alignment for thought-action inventory, dropped-item409 conflict with unchanged state, save-request UUID and jsdom native-dialog methods. Full backend847/frontend516 passed locally; lint/types and nine real-browser keyboard/narrow/reminder journeys passed. Independent review clear. No runtime or learning change. See docs/slices/ci-contract-alignment.md; new remote CI must still finish.


## 2026-10-05 — Retain explicit saved-answer reuse choice

Study Tutor now retains the learner’s reuse checkbox for the same session/target conversation. Legacy records stay opted out; no automatic generation or matching/learning-policy change. Regression reproduced before fix. 35 frontend tests, lint/types/build and two desktop/narrow keyboard/re-entry journeys passed. Separate warm local full-tutor samples: first text0.825/3.261s, total5.153/7.577s; not a cold-start or quality guarantee. See docs/slices/study-tutor-streaming-plan.md and local-tutor-latency.md.


## 2026-10-05 — Study Tutor streaming

Plain explanation/hint/chat replies now display unfinished tokens before final validation/save. Structured answer checks remain buffered. Stop, stale callbacks and re-entry preserve partial work; final replies alone enter conversation history. Same model/prompt/temperature/output limit and learning policy. Backend38/frontend35 tests, lint/types/build, two desktop/narrow keyboard browser journeys and independent review passed. First-token inference can still be slow; this slice removes the buffered-display wait, not the model processing cost. See docs/slices/study-tutor-streaming-plan.md.


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

## Audio lab return context — 2026-10-04

Fixed the reproduced workspace reset when returning from the audio lab. See slices/visualizer-return-context.md for checks and remaining playback-lifecycle design. No learning-state or audio behavior changes.

## Visualizer lifecycle inspection — 2026-10-04

Browser reproduction confirms unsaved JSON is lost on route exit. The architecture contract and three implementation slices are in slices/visualizer-route-recovery-plan.md. Next: editing checkpoint, then paused media and lesson-panel recovery. Runtime remains unchanged; no success claim for recovery.

## Visualizer editing recovery — 2026-10-04

Raw drafts, applied graph, history and selected view now recover across route exits/reload. Storage denial retains tab work and offers export. See slices/visualizer-editing-recovery.md for verification and explicit remaining media/lesson boundaries.

## Paused visualizer file recovery — 2026-10-04

File/position now survive route exit in tab memory, with disposed audio resources and explicit silent Resume. See slices/visualizer-media-recovery.md for verification, tone-detour correction and remaining reload/lesson boundaries.

## Audio lesson controls — 2026-10-04

Lesson step, tone settings and hint recover across route exit/reload without autoplay. See slices/visualizer-lesson-recovery.md. Next recover comparison predictions and close source/reselection gaps; full C3 remains open.

## Comparison recovery — 2026-10-04

Selected experiment, optional prediction, hint and reveal survive lesson/route changes and reload. Explicit Restart/Stop behavior retained. See slices/visualizer-comparison-recovery.md for verification and remaining context gaps.

## File reselection — 2026-10-04

Reload now explains the missing local file and asks for reselection; replacement starts at zero. Empty chooser does not invent a lost file. See slices/visualizer-file-reselection.md for evidence and remaining presentation/context work.

## Visualizer guidance layout — 2026-10-04

Optional instructions moved below canvas/transport into keyboard-accessible details; saved summary and expanded failures remain. See slices/visualizer-guidance-layout.md for verification. No lifecycle/learning changes.

## C3 evidence contract inspection — 2026-10-04

Verified coding tutor still has no lesson retrieval and source-aware reuse. Next plan is slices/lesson-playground-evidence-plan.md; source labels must remain general until evidence/retry contracts are implemented. No runtime changes in this planning slice.


## Linked lesson request validation — 2026-10-04

C3 coding requests now validate typed lesson origin on the server while preserving completed retries and legacy fingerprints. See slices/lesson-origin-validation.md for checks and concurrency limits. Source retrieval/reuse remains next; no learning logic or routing changes.


## Grounded playground integration boundary — 2026-10-04

Source/retry inspection found a source-free prompt and disclosure that must change together with retrieval. The evidence plan now specifies bounded snapshots, cross-course provenance, source-aware reuse and completed replay without a new claim schema. Seven existing retrieval/recovery tests pass; grounded runtime remains unimplemented.


## Bounded source snapshot — 2026-10-04

Pure lesson-evidence helper now preserves whole budgeted passages, hashes and quoted provenance; 11 focused tests and static checks pass, review clear. See slices/lesson-evidence-snapshot.md. Runtime integration/reuse/source UI remains next; this does not yet enable grounded tutoring.


## Linked coding sources and reuse — 2026-10-04

Explicit linked tutor requests now retrieve local references, retain per-answer source panels and use evidence-aware exact reuse. Known availability failures disclose general help; completed retries retain original sources. See slices/lesson-playground-sources.md for55 backend tests, browser/keyboard/reload evidence and real-model semantic limitations. Starter suggestions and broader workspace phases remain open.


## Explicit starter-code help — 2026-10-04

Lesson experiments now offer a starter request and explicit Python-example append with guarded Undo. Unsent questions/existing code are preserved; no autorun. See slices/lesson-starter-code.md for tests, browser evidence and limitations. Next: local-model grounding checks and remaining contextual workspace work.


## Actual local grounding sample — 2026-10-04

Seven synthetic real-local runtime cases completed; independent review:0 full passes,6 partials,1 failure. Source/citation mechanics are not model accuracy. Fixed the numeric-vector false citation warning; see slices/lesson-grounding-diagnostic.md for methods, limits and next reasoning/starter contract work. Routing and owner data unchanged.


## Grounded explanation revision — 2026-10-04

Prompt v2 plus versioned reuse improves the bounded local sample but does not pass the quality gate. Llama:1pass/5partial/1fail; Gemma:2pass/4partial/1fail, including incorrect source attribution. No routing switch. Empty-grounded vector warning fixed. See slices/grounded-explanation-v2.md; next is a validated starter contract.


## Validated starter contract — 2026-10-04

Starter help now separates model-proposed data/result from app-owned unfinished Python scaffolding. Keyboard insertion, Undo and lesson return remain explicit; narrow conversation overflow fixed. See slices/starter-contract-progress.md for verification and remaining semantic quality limits. Full C3/design plan remains open.


## C3 work-alongside recovery — 2026-10-04

The embedded quiet-panel choice survives matching-session/tab detours and reload without audio autoplay. See slices/alongside-recovery.md for verification and limits. Source retrieval/starter scaffolding shipped separately; older TODOs are historical. Remaining project/review/audio entry contracts and C5 stay open.


## C3 task notebook re-entry — 2026-10-04

Task notebook view restores for matching course/section and starter/dataset paths; explicit return clears it. Results remain temporary; no code autoruns. See slices/task-notebook-view-recovery.md for evidence and versioning limits. Full C3/C5 remains open.


## C3 project location links — 2026-10-04

Project course/step/notebook view have URL identity and browser-history recovery; existing notes remain scoped. See slices/project-location-links.md. Relevant authored lab links remain next; full C3/C5 is open.


## C3 authored audio-lab links — 2026-10-04

Optional project-to-audio lesson relations now have validation, explicit explanation selection and named return. See slices/project-audio-lab-contract.md for synthetic browser/review evidence. No real material mapped yet; relevance requires source inspection. Full C3/C5 remains open.


## C4 map investigation and baseline — 2026-10-04

Recorded read-only area-map contract in docs/slices/area-map-plan.md. Verified stored area membership exists; map currently exposes only the whole graph. No audio mapping justified by current authored project sections. Corrected the existing mobile map journey to open its collapsed menu by keyboard before choosing Home. Both 390/1280 recovery journeys pass after the test correction; narrow screenshot inspected and focused ESLint passed. No production application or learning-logic change; no build rerun needed for documentation/test-only delta. Next: implement verified map scope with outside-area prerequisites and exact URL/cache identity. Full C4 remains open.


## C4 area map implemented — 2026-10-04

Map now offers explicit area URL scope and a global choice, using stored membership and transitive prerequisites. Outside-area prerequisites are labeled and readable as text. Learning goals/mastery/unlocks remain unchanged. See slices/area-map.md for backend/browser/build/review evidence and the native-select automation limitation. Next C4 work: organize existing Library/source discovery; persistent tutor remains C5. No broad phase closure or human-comprehension pass claimed.


## C4 Library source discovery — 2026-10-04

Library now offers Sources alongside Saved answers, reusing read-only retrieval and the source viewer with URL/history/focus recovery.15 component checks and6 browser journeys pass; final visual/lint/types/build evidence and limits are in slices/library-sources.md. Learning logic and model routing unchanged. C4 bounded implementation is present; human acceptance remains open. Next C5: inspect and define persistent tutor target/draft/stream lifecycle before changing the shell.


## C5 companion context foundation — 2026-10-04

Captured material, unapplied edits and one previous capture now survive route changes/reload; applying material explicitly separates conversation identities. Existing close/request/media cleanup remains intact. See slices/companion-context.md and persistent-tutor-contract.md for baseline, tests, reviews and limits. Next: implement desktop panel/narrow sheet using this state owner; footer placement is still temporary. Full C5 and human acceptance remain open.


## C5 responsive tutor panel — 2026-10-04

Global tutor entry, desktop panel and narrow modal sheet implemented without learning/provider changes. See docs/slices/companion-panel.md for recovery, resize, keyboard and test evidence, plus remaining human/voice gates. Narrow origin navigation closes the sheet to reveal the destination. Next: bounded C6 Home/audio/capture inspection.


## C6 Home topic disclosure — 2026-10-04

Collapsed optional topic form, retained visible selection and new-session settings summary. Learning handlers unchanged. Evidence and remaining C6 scope: docs/slices/home-topic-disclosure.md. Next: inspect audio active-stop and contextual capture before the next bounded change.


## C6 capture clarity/recovery — 2026-10-04

Save for later replaces Park; failed/timed-out save retains text with uncertainty guidance, repeated pending submission is guarded, saved-list failures are explicit. Audio active Stop confirmed already outside collapsed settings. See docs/slices/save-for-later.md for checks and remaining idempotency/context/promotion gaps. C6 remains partial.


## C6 thought draft recovery — 2026-10-04

Versioned tab checkpoint retains text, original session/skill and unconfirmed-save state; reload never submits. API text bound and storage errors explicit. docs/slices/capture-recovery-contract.md records tests and larger backend gaps. Next: saved-thought action feedback/recovery; C6/C7 remain open.


## C6 saved-thought actions — 2026-10-04

Show on Home and deliberate Remove replace misleading Promote/Drop/Done labels; pending/error/deadline/focus feedback added. See docs/slices/saved-thought-actions.md. Backend undo/idempotency are not implemented. Next: remaining Home composition/data reconciliation, then C7.


## C6 Home recent areas/reviews — 2026-10-04

Read-only recent browsing links and honest capped current-session review count added. No review-card endpoint or learning writes for decoration. See docs/slices/home-recent-areas.md. Next C6: ResumeCard intent separation/short action; C7 still open.


## C6 Home resume intent — 2026-10-04

Separated the saved-session Continue card from optional new-session preparation. Starting another lesson with an active session now uses the existing explicit Keep current / End and start flow, preventing a second session from silently hiding saved work. Details and verification: docs/slices/home-resume-intent.md. Learning kernel unchanged. Human comprehension, durable capture return/undo and C7 recent contexts/search remain open.

Final sanitized checkout verification: 16 component tests, frontend lint, TypeScript and production build passed. Existing large-chunk and spectrogram worker externalization warnings remain. Final original browser rerun: 8 passed. No live learner data used in browser tests.


## C6 capture transaction recovery — 2026-10-04
Thought creation and promotion now commit their audit event atomically with the item change. See docs/slices/capture-atomicity.md. Verified 22 backend tests in both variants, 11 browser regressions, targeted Ruff/mypy, read-only review. No UI/schema/learning logic change. Next: durable retry intent and source-return contracts; do not claim exactly-once network saves yet.


## C6 durable capture retry protocol — 2026-10-04
Added optional learner-scoped save identity with immutable payload fingerprint, conflict response and atomic replay; additive migration c945fa0137bd preserves legacy rows. Existing clients remain unkeyed. 28 backend tests in both variants, 11 browser regressions, targeted Ruff/mypy and generated frontend type check passed; review clear. See docs/slices/capture-retry.md. Next: persist frontend save identity across reload/retry, handle legacy uncertain drafts and edited content explicitly. Source return, undo and C7 remain open.


## C6 frontend capture retries — 2026-10-04
Unchanged thought saves now retain a durable identity across retries/reload; edits and older unconfirmed drafts explicitly use Save as new thought. Replayed dropped/promoted outcomes are reported honestly. No auto-submit on restoration. Verification: 5 draft tests, 14 sanitized browser journeys, lint/types, original build, visual/keyboard checks and read-only review. See docs/slices/capture-retry-ui.md. Next: typed original-context return and reversible saved-thought actions, then C7 contexts/search.


## C6 original-context contract — 2026-10-04
Inspected existing identities and ran 12 passing context/deep-link browser journeys. docs/slices/capture-context-contract.md defines typed original identity, immutable promotion provenance, stale-target recovery and implementation sequence shared with C7. No runtime change yet. Next implement typed capture context and durable storage; never use a plain historical /session link as proof of old-session recovery.


## C6 typed original material links — 2026-10-04
First durable capture context slice implemented; see docs/slices/capture-context-contract.md for exact supported types, migration, evidence and remaining limits. Uses displayed route identity, preserving source context through promotion and reload. 14 backend/8 unit checks plus browser regressions and sanitized final 6 context journeys pass. Next complete lesson/source/audio identity handling and project-notebook saved-thought acceptance before declaring source-return complete.


## C6 task starter return — 2026-10-04
Fixed reproduced saved-thought task-notebook link opening only the guide after the notebook was closed. Distinct task view now restores the starter with saved code/notes; no automatic execution. Final sanitized5browser,9unit,5backend checks passed with lint/types/build. See capture-context-contract.md for review and limits. Next: session/audio/source identities and undo; broader C7 remains pending.


## C6 original lesson return — 2026-10-04
Saved lesson thoughts now check current session/block identity before resuming. Mismatch offers explicit selected-lesson choices; no automatic replacement or resurrection. Exact evidence and remaining audio/source/undo scope are in capture-context-contract.md. Final sanitized2lesson journeys plus11pause/return regressions,6frontend and5backend tests pass; lint/types/build and review clear.


## C6 saved audio lessons — 2026-10-04
Built-in Learn steps now have durable thought links with explicit application and no autoplay; unknown steps preserve draft. Scope/evidence in capture-context-contract.md:6original/2sanitized browser journeys,5unit/5backend checks, lint/types/build and read-only review. Preset identity restoration is not implemented. Next source-viewer return and reversible thought actions; broader context/search plan remains incomplete.


Source-return groundwork: docs/slices/source-capture-return.md records the inspected direct-passage/capture contract and four passing baseline browser journeys. SourceViewer is inline, and existing passage URLs depend on search ranking. Next bounded implementation is explicit source capture plus independent chunk return; no runtime change or stage completion is claimed.


Explicit source capture/direct return is implemented; evidence and remaining acceptance coverage are recorded in docs/slices/source-capture-return.md. C6/C7 are not complete.


Source acceptance expanded: competing viewers, retained draft source, actual saved identity and15-second timeout/retry pass in four browser journeys; details in docs/slices/source-capture-return.md. No runtime change. Next: reversible saved-thought action contract.


Next C6 slice: docs/slices/thought-action-undo.md records the inspected revision/receipt/atomicity contract for safe reversible reminder actions. Four existing browser journeys passed. No undo is implemented by this plan; backend transaction evidence precedes UI adoption.


Reminder undo backend foundation is implemented (migration e167bc2359df and revisioned action receipts). See docs/slices/thought-action-undo.md for evidence. Next: connect guarded actions/retry/Undo to existing UI; do not claim end-user undo available yet.


C6 reminder Undo UI is implemented; exact retry identity, real end-to-end undo and stale-conflict evidence are in docs/slices/thought-action-undo.md. Controls are view-local, with durable server receipts. Next bounded phase: C7 typed recent destinations and actual searchable-store inventory. Human acceptance and remaining context gaps remain open.


C7 foundation: typed bounded tab-local history store and first verified search-store inventory in docs/slices/recent-contexts.md. No visit tracking/UI yet. Next: explicit resolved-view tracking and compact recent-material presentation, preserving existing recent areas and authoritative resume.


C7 first recent-material UI now records loaded sources and known standalone coding workspaces, with keyboard return/clear and unchanged learning state. Evidence in docs/slices/recent-contexts.md. Other destination integrations and global search remain next.


Recent material now includes resolved saved explanations and displayed audio lessons; source/project/learning state contracts remain distinct. Evidence in docs/slices/recent-contexts.md. Next: project/checkpoint recent destinations.


Recent project views and guarded lesson checkpoints are implemented; tests and limitations in docs/slices/recent-contexts.md. Next: reconcile area history and complete search-store inventory; preserve authoritative Resume.


C7 area history now shares the Home disclosure while retaining its validated area-picker store. Additional skill/project/notebook/thought search inventory and the next two-provider search slice are recorded in docs/slices/recent-contexts.md. No global-search completeness claim.


Material-search slice: Library /search now searches saved explanations and source passages independently, with URL query and separate retries. Original3 browser journeys, lint/types/build passed; review clear. Details and remaining C7 scope: docs/slices/recent-contexts.md. No learning logic changes.


Persistent header search implemented;5 original browser journeys and lint/types/build pass. See recent-contexts.md for startup dependency diagnosis and outstanding mobile chrome/search scope.


2026-10-05 header spacing: brand and search share a wrapping row on narrow screens. Screenshot shows header reduced from276px to243px at390 width; no controls hidden or learning logic changed. Five original search/keyboard/Back journeys, lint and types passed. Narrow screenshot inspected. Broader mobile composition and command access remain open.


Quick navigation implemented: header modal and Ctrl/Cmd+K, local page filtering, explicit material search, Escape with retained workspace. Seven browser journeys pass in both checkouts; lint/types and review clear. Details and remaining gates in docs/slices/recent-contexts.md.


2026-10-05 brand foundation: authoritative palette supporting tokens, local Inter/Roboto Mono, original book/connected-path mark and favicon. Assessment, font provenance, conflicts and remaining acceptance: docs/design/BRAND-FOUNDATION.md. Original11 browser checks, sanitized4, lint/types/build and read-only review passed. No learning logic changes.


2026-10-05 accessibility follow-up:320px with200% root text enlargement exposed the quick-menu Close button scrolling away. Dialog heading/Close now sit outside its scrolling content. Final enlarged-text and font-failure journeys pass in both checkouts; screenshot inspected. Original six-brand baseline passed; final relevant two rerun after layout refinement. Lint/types/build pass with inherited warnings. This is text enlargement, not browser zoom or complete accessibility certification. No learning logic changes.


2026-10-05 Library typography: Search, Sources and saved-answer list/detail h1 now use existing22/30 page-title token; Search panels use16/24 heading token. No semantic, prose or behavior changes. Original13 search/brand journeys, lint/types pass; sanitized6 source/answer journeys pass using8011/5175 because8010 was occupied. Dark narrow screenshot inspected; read-only review clear. Other screen headings remain a separate adoption step.


2026-10-05 C7 area search: Search now reuses the bounded shared area catalog to match names, descriptions and topic terms by case-insensitive phrase. Separate result group, count/8-result cap, retry and exact browse links; opening an area does not start/change a session. Eight browser journeys pass in both checkouts, including unavailable retrieval alongside area results and zero learning writes; lint/types pass, narrow screenshot inspected, read-only review clear. Used separate sandbox ports8011/5175 and search-area-check.db. Project/skill/notes search and broader accessibility/human acceptance remain open.


2026-10-05 C7 project-guide search: separate validated/bounded manifest query searches course/section titles and explanations; exact course+step guide links, cap8 and total count.404 reports no guide; invalid/unavailable data gets independent retry. No notebook cells/notes indexing or code execution. Original9 and sanitized9 journeys pass; final sanitized rerun uses explicit404 default fixture so unrelated tests cannot read owner material. Lint/types pass, narrow layout inspected, read-only review clear. Skill/notes search and broader acceptance remain incomplete.


2026-10-05 skill search: read-only catalog title/description matching, capped results, prerequisite status without fabricated mastery, exact existing lesson-choice links. Ten browser journeys pass in both variants, including no learning writes from result navigation; lint/types pass, narrow screenshot inspected, read-only review clear. CURRENT-WORK now begins with a reconciled execution checklist superseding historical next-step paragraphs. Search category orientation and broader daily-learning acceptance are next; notes/notebook search remains excluded.


2026-10-05 result orientation: compact native jump links reach all five search-group headings, preserving query and focusing the target without reissuing searches. Original11 browser journeys and sanitized focused journey pass; lint/types pass, narrow screenshot inspected, review clear. This reduces forced scrolling but does not establish owner comprehension or close the broader search/accessibility phase. Next: integrated daily-learning journey and reproduced usability blockers; retain notes/notebook search exclusions.


2026-10-05 daily-learning acceptance: initial17-test batch had one late review-next/pause failure; three isolated repetitions and full17-test rerun passed, plus6 recovery journeys. Failure remains open, not fixed. Desktop/narrow screenshots inspected; narrow explanation is below the first viewport (S2). No runtime changes. See ux/DAILY-LEARNING-ACCEPTANCE.md for evidence and remaining gates.


2026-10-05 Review pause intent: deterministic delayed-Home regression failed before fix, passes after synchronous intent invalidation. Late block response preserves server progress but cannot reclaim navigation after explicit Pause. Original13 unit/10 browser checks, lint/types/build pass (inherited build warnings); keyboard/narrow screenshot inspected; independent review clear. See ux/DAILY-LEARNING-ACCEPTANCE.md. Other navigation exits and narrow lesson hierarchy remain open.


2026-10-05 Session pause ownership: two delayed-destination tests failed before fix, pass after parent-owned guard covering async block responses and cache-driven review/recap redirects. Committed state survives and explicit resume works. Original10 unit/11 browser, lint/types/build pass; keyboard/narrow visual checked, independent review clear. See ux/DAILY-LEARNING-ACCEPTANCE.md. General non-Pause navigation remains unverified; crowded lesson layout remains open.


2026-10-05 reading order: topic heading precedes plan metadata; optional Alongside/coding follow lesson; repeated intro shortened. Start explanation moves~150px earlier at390px/~100px at1280px. Original10 unit,6 initial and6 final browser journeys, lint/types/build pass; keyboard320/390/1280 and narrow visual checked; independent review clear. No learning logic changes. docs/slices/lesson-reading-order.md records evidence and remaining control-stack/discoverability work; DL-02 stays partial.


2026-10-05 compact lesson controls: Pause/End visible, topic/labels/Undo in named native disclosure, status/errors stay visible. Review default unchanged. Original12 unit,13 initial browser +2 opt-in re-entry pass; final label/layout checks pass, lint/types/build pass. Stale persona assertion updated to actual accessible next-step description, without dropping checkpoint/draft checks. See slices/compact-session-controls.md for measured mobile improvement/desktop row tradeoff and remaining first-viewport/assistive/human gates.


2026-10-05 explanation entry: action group follows its heading, with help text below; duplicate teaching-overview instruction removed. Goal still precedes action; all audio/learning logic unchanged. Original10 unit/6 browser, lint/types/build pass, independent review clear, narrow visual inspected. Button fits the390×900 empty fixture, not320 or arbitrary content. Next inspect prepared explanation→question→feedback as one journey; see slices/lesson-reading-order.md.


2026-10-05 owner visibility/efficiency update: sanitized repository made PUBLIC after clean-index publication check and all reachable history scan (2746 blobs, no prohibited path/source identifier or credential-pattern findings); original archive verified PRIVATE. No releases, wiki or Pages; CI artifacts are sandbox journey traces. AGENTS.md now records focused context, bounded reviews, coherent slices and reuse of passing checks without reducing quality gates. This overrides earlier both-private notes.


2026-10-05 long reading re-entry: two prepared browser baselines reproduce missing section reader and question continuation after completed-response reload. Text and archived notes survive. No runtime change. See slices/lesson-reading-reentry.md for bounded recovery plan and evidence limits.


2026-10-05 completed lesson re-entry fixed: versioned optional completion metadata restores reader position, notes, sources and question action without regeneration. Legacy/partial/corrupt records remain honest; size fallback preserves text.39 unit/6 browser, lint/types/build pass; narrow visual and keyboard checked; independent review clear after bounds fix. See slices/lesson-reading-reentry.md. Next: integrated incorrect-answer feedback/help.


2026-10-05 assessment/explanation return: real wrong-answer tests reproduced feedback loss. Assessment now retained during in-page explanation visits, with hidden query/help/audio inactive and explicit Return to your question. No grading changes.29 unit/7 browser baseline, final29 unit/2 affected browser, lint/types pass; build before copy-only adjustment, visual/keyboard checked, review clear. See slices/assessment-explanation-return.md. Broader reload/pending-submission and repeated-error gates remain.


2026-10-05 checked-question reload: activity-scoped pointer restores original server feedback via GET only, preserving question snapshot and historical-result semantics. Explicit next clears pointer; lookup/storage failures remain visible.36 unit/7 browser, full lint/types/build pass, narrow/keyboard checked, independent review clear. See slices/assessment-reload.md. Older no-pointer sessions and pre-delivery uncertainty use existing archive/recovery; broader races and repeated-error guidance remain.


2026-10-05 transition outcome message: real lost-delivery tests proved server advancement despite the old nothing-changed notice. Errors now give an honest uncertainty message and existing Pause/Home/Continue recovery.23 unit/11 browser, lint/types pass; narrow visual/keyboard and read-only review clear. See slices/transition-outcome-message.md. No learning/routing change; prolonged request handling remains open.


2026-10-05 prolonged transitions: delayed status after15s explains uncertainty and Pause recovery; retries explicitly disabled. Practice Log/Skip reflect pending transition. Original28 unit/11 browser, lint/types/build pass; final narrow visual and keyboard checked, independent review clear. See slices/prolonged-transition-status.md. No learning-policy change; execution bounds and broader reliability/learning acceptance remain open.


2026-10-05 local tutor latency: configurable30min model residency for local complete/stream reduces reloads after short study breaks.39 affected backend checks, Ruff/full mypy pass; real adapter confirms30min expiry. Models, prompts and learning policy unchanged. See slices/local-tutor-latency.md for measurements, memory tradeoff and open end-to-end performance work.


2026-10-05 performance profiling: model processing dominates isolated17.38s/8.02s local turns. Prompt reorder speedup rejected after local quality fell4/5→1/5; candidate source/tests reverted. See slices/local-tutor-latency.md for limitations and an unrelated baseline parking409/400 test mismatch. No new runtime change.


2026-10-05 first-text timing: actual lesson has null memory score; rounding rejected as irrelevant. Batch512/1024/2048 has~12.3s prefill throughout, so defaults retained. Stream records now distinguish first_token_ms from total time, without generation/accounting changes.53 backend checks plus final18 accounting checks pass; Ruff/mypy and independent review clear. Real isolated timing agrees with preparation+provider elapsed. See slices/local-tutor-latency.md; latency remains open.


2026-10-05 next performance slice: Study Tutor buffers ordinary replies until complete, unlike session SSE. Documented a single streaming vertical slice in slices/study-tutor-streaming-plan.md with unchanged prompts/routing, authoritative final checks, retained partial text and durable recovery. No runtime change yet; next implement and test that contract. Do not remove bounded history or enable saved reuse silently.


2026-10-05 browser contract and Home text-size repair: streaming companion fixtures, disclosure/mobile navigation journeys aligned with actual UI; Home choices stack at narrow container sizes without changing learning behavior.16 affected browser checks plus final keyboard/text-size check passed; frontend517, lint/types/build passed. Initial Review recovery failure did not recur in unchanged focused/full reruns; cause remains unproven. Independent review clear. Full remote browser run remains open. See slices/browser-contract-and-home-text-size.md.


2026-10-05 saved-answer follow-ups now stream through shared bounded transport while preserving parent context, original request recovery and save receipts. Partial text survives Stop/re-entry without becoming learning evidence.33 backend plus final4 failure checks, frontend520, four desktop/narrow browser journeys, lint/types/build pass; independent review clear. Real local synthetic sample first13.053s/complete14.915s: first-text latency remains open. Existing inappropriate code-output notice on a non-code parent identified for a separate fix. See slices/saved-answer-streaming.md.


Full remote browser run37319478975 (preceding70feac6) finished:228 passed,20 skipped,3 failed. Remaining: Home adaptation suggestion overflows at320px/200% text sizing (Choice stacking fixed the previously reproduced control overflow but not this separate populated card); visualizer coordination journey cannot locate the global Stop visualizer sound button; narrow visualizer canvas exceeds the expected500px top position. All other CI jobs passed. These are remaining release gates, not failures resolved by follow-up streaming.

Final saved-answer streaming verification: full backend857 passed; sanitized shared-transport checks and type checking recorded separately.


2026-10-05 local tutor preparation: successful NEW-session delivery schedules optional empty local-model loading, with loopback/non-cloud guards, fresh DB, bounded job and distinct diagnostics. No prompt/model/learning change; existing-session resume is not covered. Full backend869, focused39, mypy200/Ruff and seven session browser checks pass; review lifecycle finding fixed and rechecked. Isolated fixed-prompt comparison: first text13.115s cold vs6.060s after preparation, identical output; preparation was done beforehand and this is not a quality verdict. Two stale follow-up retry browser fixtures corrected and both pass locally. Three pre-existing Home/visualizer CI failures remain. See slices/local-tutor-preparation.md.


2026-10-05 explicit resume preparation: Home Continue and Keep current session now request optional local loading without waiting. Ordinary GET/navigation remains read-only; ownership/ended guards and unchanged saved state verified. 47 backend checks, six browser journeys, lint/types/build and independent review pass. Direct-route re-entry, prompt processing and the three earlier CI UI failures remain open. See slices/local-tutor-preparation.md.


2026-10-05 browser release gates: reproduced and repaired all three outstanding Home/visualizer failures from run37324111481. Suggestion-card reflow, visible global audio Stop test, and duplicate preview padding; no learning/audio behavior changes. Fifteen journeys, lint/types/build and review pass. See slices/browser-reflow-repair.md; latest-head full CI remains open.


2026-10-05 context-allocation latency experiment: identical synthetic requests at32768 vs8192 yielded only~0.04s median first-text difference across four isolated samples. No runtime setting changed; larger-context support retained. Exact saved-answer reuse inspected, main-session automatic replay still requires its own learning-evidence contract. Next matched-model prefix/semantic evaluation; see slices/local-tutor-latency.md.


2026-10-05 matched-model latency investigation: candidate repeated-turn first-text median1.347s vs5.531s current; hard checks8/10 vs6/10, but semantic weaknesses and deployed-setting/runtime gaps prevent rollout. No app prompt change. Full browser CI37327101830 passed; fixed backend formatting and stale resume unit expectation, full frontend520 plus backend16 pass. See slices/local-tutor-latency.md and matched-prompt-order-sample.json.


2026-10-05 full-runtime Socratic investigation: three current and six candidate synthetic local turns at deployed temperature0.3 expose conflicting scaffold instructions and insufficient question givens. Both prompt candidates reverted after semantic review;34 functional checks were not a teaching-quality pass. No runtime change. See slices/local-tutor-latency.md and socratic-runtime-candidates.json. Next: concrete source-complete question and response-continuation fixtures before any prompt rollout.


2026-10-05 continuation inspection: full public CI run37329042232 at runtime9d05f91 passed all five jobs, including browser journeys. Checked-feedback discussion remains unimplemented; source inspection found hidden assessment panels stay mounted and the existing follow-up chooses a global session. The next integration must bind session identity and deactivate requests on phase exit. Exact scope and acceptance are recorded in slices/assessment-followup-context.md. No runtime change or new UI verification claimed.


2026-10-05 checked-feedback discussion shipped: explicit collapsed entry uses immutable saved parent and bound session; close/phase exit stops streaming/media while preserving mounted replies and save receipts.13 focused component tests,2 sandbox desktop/narrow keyboard journeys, TypeScript/build/lint and independent review pass. See slices/assessment-followup-context.md for evidence and remaining receipt-recovery/whole-route persistence limits. No grading/model/prompt change.


2026-10-05 assessment save recovery now enables in-session discussion immediately via existing saved-ID callback; no regrade/generation.17 component tests,2 desktop/narrow keyboard browser journeys, types/lint and review pass. See slices/assessment-followup-context.md. Whole-route unsaved-reply recovery remains outstanding.


2026-10-05 unsaved follow-up recovery retains the durable retry identity through failed save; explicit retry after same-tab/session refresh replays the completed server reply, and successful save clears the identity.12 frontend/11 backend tests,5 browser journeys, types/lint and review pass; narrow visual/keyboard checked. See slices/assessment-followup-context.md for retention/receipt limits. No automatic regeneration.


2026-10-05 assessment-origin candidate rejected:18 structural tests passed, but14 synthetic local replies exposed learner/tutor attribution failures and incorrect arithmetic across Llama3.1:8b and Gemma3:12b. API/test candidate reverted; no routing/prompt change. Evidence and next flat-context comparison are in slices/assessment-followup-context.md and assessment-origin-local-sample.json. Original-answer continuity beyond the direct parent remains open.


2026-10-05 assessment discussion now shows the saved question and displayed learner answer in an independent read-only panel.4 component tests,2 desktop/narrow keyboard journeys, types/lint and review pass; screenshot inspected. Another flat-context model sample rejected; no inference/prompt/routing change. See slices/assessment-followup-context.md. Longer-term attribution and expanded-panel density remain open.


2026-10-05 live runtime refreshed after proving old API lacked shipped streaming/preparation endpoints. Current backend health and all three paths verified through live OpenAPI; both frontend addresses reach it. Startup applied existing migrations. See slices/local-tutor-preparation.md. No new speed benchmark or code change claimed; backend remains non-reloading and needs deliberate refresh after Python edits.


2026-10-05 current local diagnostic:3 synthetic/disposable explicit TutorTurns first-text6.44/2.06/2.04s, total13.05/7.64/8.74s after2.70s preload. See slices/local-tutor-latency.md and current-tutor-timing-sample.json for warm-cache/retrieval/raw-preview limits. No runtime changes, no owner learning activity, no broad speed/quality claim.


2026-10-05 local Session output-cap safeguard: explicit Ollama length termination now marks a reply partial and prevents completed-history save, preserving text/accounting/replay.72 backend tests plus final7 API checks,3 browser journeys, Ruff/format/full mypy and review pass; local adapter smoke and narrow visual/keyboard verified. See slices/local-tutor-latency.md. Other providers and Study Tutor/follow-up consumers remain separate work.


2026-10-05 streamed Study Tutor and saved discussions reject output-limit completions while retaining preview/draft and original retry identity.28 focused backend tests, full mypy, lint/format, narrow keyboard browser test and review pass. No completed-answer/assessment writes or duplicate retry generation. See slices/local-tutor-latency.md; buffered/structured paths remain separate.


2026-10-05 full verification:879 backend tests pass; public CI37337784627 at6925265 passed. Buffered termination handling requires a separate accounting/no-regeneration contract; documented in slices/local-tutor-latency.md. No runtime or learning-policy change. Latency and broader learning acceptance remain open.


2026-10-05 semantic history precheck skips model discovery when eligible answers have no vectors, preserving indexed-candidate validation.28 backend tests,4 browser journeys, lint/format/full mypy and independent review pass. See slices/local-tutor-latency.md; generation latency remains open.


2026-10-05 isolated local cache experiment found empty resume preparation preserves the warm prefix in the tested runtime. No preparation/prompt change; raw synthetic evidence and limits in slices/preload-cache-sample.json and local-tutor-latency.md. New-context processing remains open.


2026-10-05 buffered plain-text output caps now reject after usage accounting, without regeneration or completed-history save.887 backend tests, full mypy/lint/format, narrow keyboard browser regression and independent review pass; real local adapter smoke verified. Structured policy unchanged. See slices/local-tutor-latency.md for scope and remaining provider/message limits.


2026-10-05 review concept help is available after reveal without rating/hint writes; collapse/rating stops help and reopening retains text.16 unit tests,2 desktop/narrow keyboard browser journeys, lint/types/build and independent review pass. See ux/DAILY-LEARNING-ACCEPTANCE.md. Lower-credit execution rules recorded in AGENTS.md; broader performance/UX gates remain open.
