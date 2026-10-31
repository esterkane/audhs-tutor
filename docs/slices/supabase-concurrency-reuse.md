# Reviewed concurrency incident answers

Two reported PostgreSQL conditions now reuse reviewed bilingual explanations rather than asking
local generation to invent diagnosis or SQL: serialization_failure (40001) and deadlock_detected
(40P01). Exact SQLSTATE-labelled reports and the corresponding canonical English server messages
are recognized. A bare numeric value, generic lock timeout, hypothetical/denied report or a report
also explicitly naming an unhandled SQLSTATE delegates to the ordinary tutor. This is a bounded
answer-reuse strategy, not a general decoding or open-ended factual-accuracy improvement.

The answer explains the complete transaction retry boundary, statement/value selection, ending the
failed attempt, bounded retries and external effects. It distinguishes Repeatable Read from the
unsupported inference that every 40001 proves Serializable isolation, and distinguishes a deadlock
from an ordinary lock timeout. It never identifies a culprit table, index, role or RLS policy from
the code alone. No generated SQL or automatic retry/execution is introduced. Mixed reviewed
conditions retain their separate meanings; an empty diagnostic SQL block is omitted.

Sources checked against PostgreSQL 17 documentation:
- [Serialization failure handling](https://www.postgresql.org/docs/17/mvcc-serialization-failure-handling.html)
- [Deadlocks](https://www.postgresql.org/docs/17/explicit-locking.html#LOCKING-DEADLOCKS)
- [Error codes](https://www.postgresql.org/docs/17/errcodes-appendix.html)

Socratic delivery, active labs and non-incident modes do not enter the new reuse path. No ledger,
mastery, learner root cause, evidence or remediation is inferred. All existing transcript and
learner-edited fields remain under their original persistence/ownership rules.

Measured on the configured local stack with disposable learner identities and synthetic incidents:
- One baseline 40001 question took 47,387 ms and echoed the question without explaining recovery.
- The same question returned the reviewed answer in 27 ms. Additional English 40001 and German
  40P01 probes returned in 26 and 22 ms; each restored two transcript rows and recorded zero new
  model calls. These are end-to-end API samples, not a latency distribution or decoding benchmark.
- 77 affected backend checks pass, including German/English content, refusal boundaries, mixed
  messages, no model call and preserved input history. Ruff and strict mypy (327 files) pass.
- Configured-stack Chromium journey passes (13.1 s total): existing privilege/schema/mixed reports,
  both concurrency replies, reload with all ten transcript rows, retained learner hypothesis,
  390px overflow/axe, project notes save/reload and knowledge-authoring handoff.
- Full isolated focused upload → research → write → Library reopen → review → activate → reading,
  notes, pause/resume, check/feedback → recap → Library search journey passed separately (16.5 s total).
  Its assessment uses explicit uncertainty confirmation, not real-model grading certification.

No hosted requests, credential/cap changes, schema migration or private archive changes. Full
backend/frontend baselines are supplied by the preceding exact-head CI; the browser job was still
running when first checked. Reuse does not qualify unfamiliar incidents beyond these boundaries.
