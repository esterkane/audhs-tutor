# Honest provenance for saved research history

An API regression demonstrates that authored/imported tutor history can contain an arbitrary
answer and a calculation/reference identity. These fields describe the saved record; they are
not a server-issued authenticity receipt. The reuse HMAC protects exact optimization eligibility,
but the UI cannot validate it and it does not certify imported display history.

The reader therefore labels saved calculation and reference replies as provenance unverified.
It does not claim that a calculation or model did/did not run based solely on imported fields.
Source links and quotations remain inspectable, with their existing limits. All original answer
text, identities, findings and complete histories are preserved; no learner writing is silently
corrected, discarded or relabelled as model output. Genuine checked-answer computation, source
validation, reuse signatures and local/hosted routing are unchanged.

This fixes unsupported presentation claims. It does not authenticate historical records or fix
incorrect imported prose. A future verified badge needs durable server-owned receipts bound to
the answer, source, checker/policy version and learner; it must handle edits, imports and API
restarts without trusting client-supplied flags. Do not invent a verified flag in the client.

Verification: synthetic API import/read proves arbitrary labelled text is retained without any
model call. Component regressions fail the old certification wording and pass the cautious labels.
Responsive browser checks confirm fabricated text stays visible with unverified provenance before
and after reload. Real calculation/reference, reuse-at-capacity, authoring, accepted reading,
feedback, recap and save/resume journeys remain covered. No real learner records are used.
