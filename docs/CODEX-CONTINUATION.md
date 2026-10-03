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
