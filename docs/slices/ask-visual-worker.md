# Ask local graph worker

A learner-requested saved-answer visual is generated locally from its exact reserved
binding, using a bounded non-executable graph proposal and server-owned provenance.
This worker adds no endpoint or automatic generation. It emits model-call and tutor
traces, never assessment, competency, memory or session events. Mode/energy and
learning logic are unchanged. Text equivalents are mandatory; rendering remains the
existing keyboard-accessible graph/text component. API/UI integration follows.

## Implementation and gates

- Claim once; duplicate/terminal starts never infer again. Every repair/fallback
  rechecks source currency/trust and consumes the shared durable attempt budget.
- Fresh consistent input read, bounded to 48,000 UTF-8 bytes without silent truncation.
  Only root question/answer/purpose and current lineage sources enter quoted data;
  private raw lineage metadata is not sent wholesale. Unknown grounding is blocked;
  source-free drafts stay ungrounded. Transport remains verified local by the gateway.
- Model proposes at most 16 nodes/32 edges with text equivalents, labeled relations,
  valid endpoints and source membership. Identity, binding and origin are server-owned.
- Revalidate and atomically save version, completion and trace. Cancellation/error
  cannot revive a deleted request. No writer lock is held during model inference.
- Fake-provider verification is not evidence of live diagram correctness or latency.
  Explicit start/status/cancel routes, Ask controls and live synthetic quality review
  remain outstanding. No new API, migration, dependency or browser flow in this slice.

## Verification and review

1548 backend tests passed (3 warnings); full lint/types passed. After the review fix,
16 worker/context tests and 57 affected prompt/Ask/assessment/history tests passed;
strict typing and targeted lint/format passed again. Fake providers and disposable
DBs only: no paid or live-model calls, learner data or browser claims.

Required code/pedagogy review found numeric trust headers could be mistaken for
factual reliability. Worker prompts now omit those numbers while trust enforcement
remains active; a sourced prompt regression covers this. Reviewer cleared the fix
with no remaining blockers/majors. Semantic quality still requires local trials.

Pedagogy: optional representation of a requested explanation; no Socratic switch,
compulsory confidence, fabricated assessment or FSRS scheduling. Grounding and
uncertainty remain visible; schema validity is not accuracy.
