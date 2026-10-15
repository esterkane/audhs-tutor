# Owned checkpoint API transaction

Existing session detail and checkpoint endpoints load a session by raw ID. Checkpoint merges happen without the SQLite lifecycle lock or an ended-state check. This permits foreign reads/writes and late checkpoint saves after completion; independent workers can also merge stale block state.

Use the existing owned lookup for session detail. Wrap the checkpoint handler's existing merge/validation in `open_transition`, scoped to the resolved learner, and defer its inner save until the outer commit. This serializes with Finish/advance/standalone plan mutations and returns the existing completed-session conflict. Preserve allowed phases, reserved keys and optional block-index validation. No new learning decision, schema, UI or optimistic revision protocol.

Expected files: api/sessions.py, focused tests and documentation. Verify foreign/missing equivalence, unchanged DB on rejected writes, both checkpoint/lifecycle orderings, rollback/cancellation and existing owned browser journeys. This does not certify internal tutor checkpoint writers, adaptation decisions or same-block semantic request ordering; those require separate evidence.
