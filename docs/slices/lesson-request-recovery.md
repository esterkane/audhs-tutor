# Lesson turn request recovery

Status: backend foundation verified; browser and voice integration remain pending.

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

## Next UI slice (not implemented here)

- Add server replay metadata and visible recovered-result wording. Applying old meta must not
  lower/change the current block's hint evidence or retarget its skill; currently TeachPanel
  applies meta.hint_level through onHintLevel, so this needs explicit replay/context gating.
- Persist request identity and original payload scoped to session/block/skill; preserve unsent
  drafts across target changes. Do not blindly key/remount TeachPanel and lose its input.
- Retain delivered partial text across reload separately from server-confirmed completion, with
  bounded storage and honest failures. Preserve previous text during retry and explicit new work.
- Parse HTTP claim conflicts into clear retry status; no silent inference restart. Test reload,
  stopped/cancelled streams, stale callbacks and live progress changes with actual event counts.
- Offer explicit retry/discard/storage-denial controls; no automatic audio on recovered results.
- Then design voice turn identities separately: capture, interruption and playback cannot be
  treated as interchangeable with text SSE. Personal-recording benchmark gate stays open.
