# Atomic next-activity transition

Reproduced: injecting failure in the next block start leaves the previous block's end event/checkpoint committed. The endpoint already promises atomic end-and-start; this is a transaction defect, not a new learning rule.

Bounded fix: share the owned session writer-lock primitive with finish; refresh ended state before reading the checkpoint; reject an ended session; stage block end and next start with deferred commit; commit once and roll back exceptions/cancellation. Preserve from_index replay semantics, grasp checks, optional blocks, timer values, event order and standalone start/end defaults. No schema or UI changes. Competing advance/finish workers must serialize; direct start/extend/replan writers are not covered by this bounded claim.

Expected files: kernel/blocks.py, kernel/session.py (rename lock helper for its shared scope), api/sessions.py (updated helper name), focused regression tests. Use disposable HTTP and independent-session tests; no live learning or inference required.

Review finding: the writer lock matches the supplied session row’s learner_id; it is not caller authentication. Existing block endpoints load by session ID without a Learner ownership check. This change preserves that inherited behavior, not certifies it. Next bounded fix should validate caller ownership across block read/start/end/next/extend/replan before mutation, with wrong-owner/no-write tests.
