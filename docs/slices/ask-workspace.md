# G1 — Session-independent Ask workspace

Status: implementation in progress. Home inspection confirms no standalone question
entry; StudyTutor currently requires a session. Add /ask and explicit Home/Tools
links without changing the five primary navigation destinations or learning logic.

The learner chooses an optional area, types a question or selects a locally saved
question, receives a streaming explanation, and can continue from a saved answer.
No session, competency, FSRS or adaptation write occurs. No course/page context is
attached automatically; this first slice labels answers unverified and unsourced.
Detailed grounding/reference checks and content promotion remain G2–G6 work.

## Identity and recovery

One additive learner-scoped AskRequest table stores durable UUID intent claims and
fingerprints. Equal key/payload replays; mismatched payload conflicts; unresolved
claims never regenerate automatically. No model work holds a write transaction.
Save the nullable-session TutorAnswer and completed request receipt atomically.
Conversation identity is a root request/turn ID plus explicit parent-answer links, not
an invented Session. Follow-ups read only owned Ask ancestry, at most three prior
turns, disclosed in the UI; sibling follow-ups are independent branches.

Browser state preserves draft, response preview and pending request identity.
Stop aborts display/generation where supported but retains work; uncertain outcomes
use explicit recovery. New topic never changes the current learning session.
Saved-question suggestions use local FTS with literal prefix matching, exclude
negatively reviewed/replaced answers, and never call a model while typing.

## Planned files and gates

New schema, request service, orchestrator/API, migration, prompt, Ask route/API and
focused tests. Small changes to answer persistence/search, navigation/Home and
shared streaming/retry primitives. Existing tokens, Markdown and audio controls;
no new library. Use the shared design system; one composer, explicit saved/check
status, keyboard suggestion buttons and narrow-screen reflow.

Verify learner isolation, duplicate/conflicting/concurrent claims, incomplete
streams, no learning writes, atomic save/replay, backup/export/wipe/migration,
stale searches, double submit, Stop, reload/navigation recovery, denied storage,
keyboard/mobile/zoom and real local generation separately from FakeProvider tests.
Required code/pedagogy review and human/AT limitations recorded before publication.

## Verification checkpoint — 2026-10-12

- Eight Ask backend regressions plus migration-upgrade regressions: 16 passed.
  Includes owner-scoped receipt export/wipe and refusal to downgrade while an
  unresolved receipt exists. DB-core/Ask subset previously passed 11 tests.
- Strict mypy passed all 238 application files. Targeted Ruff, frontend ESLint,
  TypeScript and production build passed (existing large-chunk warning remains).
- Five isolated Chromium journeys passed at 390/1280 widths: keyboard suggestions,
  double submit, saved follow-ups, reload/Back, unchanged session, partial-response
  replay, Stop, denied-storage navigation, and replay with an unavailable parent.
  These use response fixtures; they do not establish real-model factual accuracy.
- Narrow screenshot inspected: composer, local suggestions, saved-state wording and
  navigation reflow without horizontal overflow. Full zoom/AT and human clarity
  acceptance remain open.
- Required bounded review found a frontend replay gate depending on parent loading.
  Fixed: exact pending retries bypass that mutable context gate; new requests still
  require it. The unavailable-parent browser regression now passes.
- Live Home link and Ask page were visibly checked; backend OpenAPI exposes both
  Ask endpoints. No question was submitted against the owner's learning database.

Remaining before slice publication: finish full backend result review, final
review acknowledgment, trace/prompt evaluation and local-model sample, migration
and backup verification, documentation reconciliation and paired sanitized/private
commits. G2–G6 source verification, references, visuals and content promotion remain
separate work; do not mark the complete content workspace delivered.

Audit note: Ask currently records gateway model_call metadata and saved-answer
prompt identity, but no TutorTrace. Existing TutorTraceRecord requires a session_id.
Resolve session-independent tracing deliberately before publication; do not invent
an artificial learning session to satisfy the trace schema. Full backend run is
currently active in terminal session15329, log /tmp/ask-full-backend.log; inspect
that handle before starting another suite.

### Tracing follow-up

The previous full backend run completed: 1,370 passed, three warnings. Subsequently,
added nullable TutorTrace session binding via a separate reviewed Alembic migration;
existing traces remain unchanged and downgrade refuses sessionless-history loss.
Ask now saves the tutor trace atomically with answer/receipt and links the actual
model_call, latency, prompt version and omitted older ancestry. No synthetic Session.
Seventeen affected Ask/migration/export tests and strict mypy passed; migration
verification succeeded on a disposable consistent owner-DB copy. Live DB migration
has not been applied. Final trace-downgrade regression is in test_ask.py; latest log
/tmp/ask-trace-guard.log. Supersedes the missing-TutorTrace audit note above.

### Local-model smoke sample and final review

Two synthetic streamed turns ran through the real Ask orchestrator/gateway using
local llama31-8b and a disposable DB; no hosted provider was configured and budget
was zero. First-token/complete latency: 3.22/5.91 seconds for an explanation and
0.23/1.90 seconds for its follow-up. The answer correctly calculated 1,000 weights
as 4,000 versus 1,000 payload bytes and the follow-up rejected the false claim that
fewer bits always improve accuracy, without forcing a quiz. The first answer's
“especially large values” caveat is oversimplified: quantization error depends on
range/scaling and clipping. This is two-turn smoke evidence, not a factual-quality
or learning-outcome gate; reference checking is still absent. Raw local output:
/tmp/ask-local-sample.json (synthetic only, temporary).

Required reviewer accepted the pending-retry fix and found no blockers in nullable
session tracing or atomic answer/trace/receipt writes. Eight targeted shared
stream/recovery hook tests pass, including Ask identity across remount with denied
storage writes. Whole-repo lint and strict typing pass. The final full backend run
is terminal session83669, /tmp/ask-final-suite.log; wait for it before publication.


### Final G1 acceptance checkpoint

Final full backend suite: 1,371 passed, three dependency warnings. Whole-repo lint
and type checking passed. Five isolated browser journeys and the reviewed mobile
render remain valid (tracing changed no UI). Required code/pedagogy review cleared.
Migrations applied successfully to the local DB at2ef8502090bd after the disposable
copy checks. G1 functionality is verified within these limits; human/AT/zoom
acceptance and broad model factual quality are not established. G2–G6 remain open.
