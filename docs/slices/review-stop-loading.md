# Review Stop while session state loads

A CI journey exposed a real race: review cards can load before session state. Stop previously interpreted missing state as no running block and opened recap without saving the block.

Stop now resolves bounded authoritative session state before ending the review block, checks the returned ended status, retains the screen with a visible retryable error on failure, and ignores stale completion after leaving the screen. The existing session-wide Stop/Home controls remain available. Already dispatched server writes are not undone by navigation.

Verification: focused Review component tests cover delayed session load, failed read then retry, and leaving while the save completes. The isolated session stop/resume browser journey passed. TypeScript and focused lint passed. Independent code review identified the stale navigation race; lifecycle guards address it. No backend/schema/model-route changes. Full cross-browser acceptance remains open.
