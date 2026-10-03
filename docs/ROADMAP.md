# Roadmap

The local-first tutor supports knowledge areas, source-based lessons, practice, review, local material import, coding and audio exploration. See README.md for setup and current capabilities. Personal corpus inventories and measured private-course results are not published.

- Shared audio controls: implemented and browser-tested (2026-10-01); physical headphone audibility remains owner verification. See docs/slices/shared-audio-controls.md.

## Task notebook round trip — 2026-10-01
Try can open a section-specific local starter with a CSV, separate inspectable calculation checks, and return checked output to preserved project notes. Edits invalidate success; Back remains available. 177 frontend tests, lint/types/build, isolated real-Pyodide Chromium journey and required code/pedagogy re-review pass. No new backend API or progress claims. See docs/slices/task-notebook-roundtrip.md.

## Inline answer feedback and question audio — 2026-10-01
Think deeper exposes Check my answer using the existing session/tutor routing; question, criteria and worked example are supplied. Selected question, revealed hint/checklist and returned feedback have explicit listening controls. Edits invalidate old feedback; text changes stop/reset speech. 180 frontend tests, lint/types/build, isolated fake-tutor Chromium journey and required reviews pass. Real model correctness and headphone audibility are not certified. See docs/slices/project-answer-feedback.md.

## Local notebook lab from app — 2026-10-01
Notebook workspace can prepare an explicit private bundle, preserve existing edits, install/repair pinned base tools on request and start loopback authenticated Jupyter. No cells execute automatically. Eight backend regressions, 181 frontend tests, lint/build, isolated browser journey and code/pedagogy reviews pass; real launch returned ready and HTTP 200. Course-specific legacy dependencies remain a separate compatibility task. See docs/slices/local-notebook-launch.md.

- 2026-10-01: bounded draw.io text ingestion implemented and reviewed; see docs/slices/diagram-ingestion.md.

- 2026-10-01: archive-member retry preserves completed work; see docs/slices/archive-retry.md.

- 2026-10-01: current tutor explanation controls implemented; Q2 remains partial, including model adherence. See docs/slices/tutor-explanation-controls.md.

- 2026-10-01: StudyTutor elapsed waiting, nearby Stop and completion announcement verified; see docs/slices/tutor-waiting.md.

- 2026-10-01: notebook native file-input width constrained; all33 local browser journeys pass. See docs/slices/notebook-responsive-input.md.

- 2026-10-01: assessment help/feedback widget identity collision fixed; see docs/slices/assessment-widget-identity.md.

- 2026-10-01: shared tutor waiting/completion and immediate playground Stop verified; see docs/slices/shared-tutor-status.md.


### 2026-10-01 — bounded workspace arithmetic feedback

Implemented literal numeric equality checks, separate from model guidance and learning evidence.542 backend tests, 228 frontend tests, lint and independent review pass. Actual local feedback still has tag/interpretation failures; full tutor quality remains open. See docs/slices/workspace-arithmetic-checks.md.


### 2026-10-01 — bounded formative answer checks

Explicit answer-check integration completed; see docs/slices/explicit-answer-feedback.md. Broader teaching-quality and unrelated gates remain open.


### 2026-10-01 — completed-answer save recovery

Retry saving without regeneration implemented. Process-bound one-hour receipts; lost-delivery and request-level inference idempotency remain open. See docs/slices/answer-save-recovery.md.


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
