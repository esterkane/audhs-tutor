# Standalone plan mutations versus Finish

## Concrete boundary

Start/end/extend use a loaded session/checkpoint without a database writer lock. Replan checks a loaded `ended_at` and commits energy before preparing its adaptation card. A request that loaded the session before Finish may therefore use stale state; a failed proposal can leave energy saved without the advertised proposal.

The bounded change shares Finish's existing SQLite writer lock for the four API mutations. An owned open-session transaction refreshes the session after locking, rejects completed sessions with the existing `session_ended` 409, commits once and rolls back exceptions/cancellation. Inner block writes and replan proposal/event creation defer their commit. No model/network work runs while holding this lock. Existing successful block rules, timer arithmetic, explicit energy changes and opt-in proposal acceptance stay unchanged.

Expected files: kernel/session.py (transaction context), kernel/blocks.py (optional deferred extension commit), kernel/adaptation.py (optional deferred proposal commit), api/plan.py, focused regression tests and slice documentation. This is not a schema or learning-policy change.

## Acceptance

Use independent request sessions and disposable data. Cover stale sessions after Finish, both overlapping writer orders, no post-Finish writes, duplicate block start/end, additive extensions, rollback after staged writes/proposal/event and cancellation. Preserve foreign-owner 404s and ordinary session journeys.

## Architectural limits

This is an API transaction boundary, not a universal lock around every kernel helper. Checkpoint writes and adaptation decision/undo also write session state and require their own scoped follow-up review; do not silently fold them into this slice. Replan proposal deduplication and additive extension retry semantics are unchanged. A committed response lost in transit is still uncertain; do not introduce automatic retries. The local current-learner resolver remains unchanged.
