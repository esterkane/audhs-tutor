# G3c — Opt-in reopening of identical saved Ask answers

Problem: submitting the same standalone question regenerates even when the owner
has marked an identical saved answer Helpful. Existing suggestions only open on
manual selection. Add an unchecked Try a saved answer first option for new questions;
when no eligible match exists, generate normally. Follow-ups always generate.

Eligibility: owner-scoped Ask answer, no ancestry/memory, explicit Helpful feedback,
existing hidden/incorrect/outdated/replacement exclusions, byte-exact question and
area, new versioned binding of full prompt packet plus selected source snapshots,
current registry identity/revision, and saved answer hash. Old unbound records stay
manually readable but never automatically reopen. Recheck direct source hashes and
local versions. Malformed/historical/negative local review receipts block reuse;
supported listed claims do not certify the whole answer. No hosted transmission.

Reuse returns the original answer/date, with a durable idempotent receipt and tutor
trace, without creating another answer/model-call/learning event. Stop and retries
reuse the existing request recovery. Original date and explicit reused status remain
visible. False/default option serializes like the old request to preserve recovery.
No migration/dependency/learning logic changes. Files: Ask schemas/orchestrator,
new read-only reuse helper, Ask UI and tests. Bound candidate and receipt scans;
full lineage/semantic reuse and factual-quality acceptance remain open.

## Review fixes and evidence

- Eligibility and reuse receipt share a short BEGIN IMMEDIATE transaction after
  claiming the request. Re-resolve source trust, model registry binding and area
  title inside it. Release the lock before any model generation on a cache miss.
  Two-session regression proves concurrent Incorrect feedback waits for the reuse
  receipt and prevents reuse on the next request.
- Require explicit receipt version/method/coverage and run load_bound_review with
  current passage text. Exact answer/quotation/hash binding and current local
  versions are checked; invented evidence quotes, malformed and negative receipts
  prevent reuse. Supported claims still do not certify correctness.
- 35 affected backend tests passed: exact replay/zero extra model calls, one saved
  answer, trace/receipt atomicity, changed question/model/text/source version,
  missing binding, hidden/Confusing feedback, follow-up exclusion, review binding,
  concurrency and unchanged legacy default fingerprints. Required code/pedagogy
  re-review cleared both findings; no remaining blockers/majors.
- All 13 Ask browser scenarios passed, including explicit checkbox keyboard use,
  reload disclosure and opting for fresh generation. Existing stop/recovery and
  source/reference journeys remain passing. Full frontend 656 tests passed.
- Final full backend: 1,445 passed (3 dependency warnings). Full lint, mypy,
  TypeScript and production build passed; existing bundle/externalization warnings
  remain. Narrow-screen screenshots were inspected; keyboard checkbox and reload
  feedback passed. Private SQLite snapshot verified unchanged in five parts.

## Limits

Only newly bound standalone answers explicitly marked Helpful qualify. Old answers
remain manually readable. Reuse scans at most20 matching candidates and25 receipts
per candidate; exceeding the review bound declines reuse. Historical negative or
unreadable reviews remain a conservative veto. Near matches and follow-ups generate.
Registry identity/revision is checked, not an independent digest of local weight
files. Unchanged local inputs do not establish current external-world facts; the
original date and absence of web refresh are displayed. This feature reopens an
unchecked historical explanation, not trusted curriculum or learning evidence.
No local-model quality experiment or speedup benchmark is claimed: deterministic
regressions prove the saved route makes no additional inference call. Broader
factual-quality, semantic reuse, full lineage and human/AT acceptance remain open.
