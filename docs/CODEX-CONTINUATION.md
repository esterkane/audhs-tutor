# Local operational notes

Personal inventories, execution logs and handoff history are kept outside the public repository.


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
