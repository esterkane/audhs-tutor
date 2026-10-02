# Assessment request recovery

Backend foundation: assessment and challenge submissions accept an optional UUID Idempotency-Key. The shared durable request ledger claims learner/session/payload before grading; matching completed retries replay the original result, changed payloads conflict, and unresolved requests never grade again automatically. Read-only lookup returns not_found/unresolved/completed for an owned session, including ended sessions. No model or evidence work occurs in lookup/replay. Existing unkeyed clients remain compatible but are not retry-protected; browser request persistence/recovery remains the following slice.

The grading pipeline has multiple commits. Interruption after any write leaves an unresolved claim, which may already have learning evidence. No elapsed timeout grants permission to rerun. This is not an exactly-once or atomic multi-write grading claim.

## Verified foundation

- Full backend613 and lint/strict types passed. Focused request suite4 passed after adding fresh-connection recovery.
- Lost response replays the identical result across assessment/challenge entry points, including ended sessions, without another attempt/evidence/model/event/history write.
- Concurrent requests run one grading pipeline. Changed payload conflicts. Cancellation after grading leaves unresolved status and never regrades on retry.
- Lookup returns not_found for another owned session and indistinguishable 404s for foreign/missing sessions.
- Code review: no blockers or majors. No browser journey claimed because browser request identity/recovery integration is not implemented in this slice.

Next slice: persist the exact UUID and frozen submission before sending; explicit read-only result lookup, bounded/stale-safe callbacks, page reload recovery, storage-denial behavior, and no silent resubmit. Cover lesson, challenge, code and listening. R3 atomic grading writes and review-rating idempotency remain separately open.

Sanitized focused ownership, assessment feedback and shared-ledger verification: 23 passed. Queue status reconciled to distinguish completed saved-history work from remaining browser/atomic-write gates.
