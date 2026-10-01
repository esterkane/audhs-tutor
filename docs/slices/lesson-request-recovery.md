# Lesson turn request recovery

Status: backend and scoped lesson browser recovery verified; voice integration remains pending.

A repeated lesson request must not repeat model calls, explained events or checkpoint writes.
Optional UUID transport identity covers the normalized lesson request across SSE and buffered
HTTP. The learner/session owns a durable claim before inference. Terminal meta and done are
persisted before delivery and replayed as the original result, including honestly partial results.
A lost stream with no persisted terminal result stays unresolved; it never restarts inference
implicitly. No new learning events, mastery changes, mode or energy adaptation on replay.

Acceptance: buffered/SSE lost delivery and cross-transport replay, actual model/event/checkpoint
counts, partial-result preservation, concurrent duplicates, owner/changed-payload protection,
final-save failure and cancellation; frontend persistent identity and explicit recovery/new-work
controls, keyboard journey, tests/lint/build and independent code/pedagogy reviews.

This is not live stream reattachment or exactly-once provider execution. Voice capture/playback
and interrupted microphone turns need a separate design and must not replay sound automatically.

## Backend foundation verification

Six regression tests cover complete/partial results through both initial transports, replay
through SSE and buffered HTTP, original terminal metadata/text, unchanged actual model/event/
answer counts and checkpoint content, changed-payload conflict, ended-session replay, concurrent
unresolved claims and failed terminal persistence. Full backend576 and lint/format/mypy/
TypeScript/ESLint passed. Required code/pedagogy reviews found no blockers or majors. Fake
providers only; no paid calls, migration, new dependency or browser behavior change.

When terminal persistence fails after teaching work, the stream retains its earlier tokens
and emits an honest failure message. The durable claim remains unresolved and forbids an
automatic rerun. On replay, text is sent as one token event followed by the original done event
so existing clients preserve partial text. Normal first-delivery streaming remains unchanged.

## Browser recovery — 2026-10-02

Lesson panels retain an exact request UUID/body, unsent draft and bounded received-text cache
in tab-local sessionStorage, scoped by session/block instance/skill. Retry and discard are
explicit; reload never submits or plays audio. Storage failures retain current work and show
recovery limits. Previous text remains available during a retry. Restored text does not restore
source-validation metadata; saved answers remain the durable source-details view.

Server replay metadata prevents recovered hints from changing current lesson hint evidence.
Checkpoint hint level initializes assessment assistance after reload. Browser regression asserts
the outgoing assessment hint count, not just the notice. Unscoped question-help callers retain
their previous ephemeral behavior; question-help durable recovery is not implemented here.

Verification: full backend576, frontend250 before final additional isolation regression; final
hook12 (including the additional isolation test), focused storage3, lint/types and production
build pass. Three isolated browser journeys cover desktop/narrow reload, exact key/body replay,
retained partial text and unsent draft, keyboard retry, and existing question-help flow. Fake
providers only; no live learner DB mutation, paid calls or audio capture. Existing bundle-size
advisory remains. Independent code/pedagogy reviews found one shared-hook major; persistence
was made explicitly opt-in, regression tested and re-reviewed with no remaining blockers/majors.

Limits: tab storage is not durable across closing/clearing the tab. Unresolved server claims do
not rerun automatically. No live stream reattachment or exactly-once provider guarantee. Voice
capture/interruption/playback needs its own identity design next. Personal voice gate stays open.
