# Ask visual generation — target preview and execution contract

## Implemented target preview

GET /api/authored-visuals/answer-target/{answer_id} resolves the owned saved Ask
answer using the existing exact question/answer/lineage hashes. It returns binding,
source IDs (at most 64, with an explicit omitted count), grounding and lineage issues.
It never returns the raw lineage snapshot, generates content, approves a visual or
writes learning state. Source-free remains ungrounded; incomplete lineage is unknown.
Missing and foreign answers have the same response. The existing single-owner local
access model is unchanged. A read result is not durable approval or trust clearance;
save/review/generation must resolve and check again in their own transaction.

No new UI in this step. An inert Generate button would hide the missing lifecycle.
This endpoint supplies the prerequisite for an actual explicit generation action.

## Architecture gap found before generation

The completed authored_visual_operation table records immutable **completed document
commands** and requires a document ID. It cannot safely reserve model work before a
document exists. Holding its SQLite writer transaction during inference would block
unrelated work; relying on process-local flags would allow duplicate inference after
restart. Do not repurpose historical command receipts as mutable jobs.

## Execution contract (partially implemented)

Reservation/attempt/atomic completion and the bounded local worker are implemented;
see visual-generation-requests.md, visual-generation-finalization.md and
ask-visual-worker.md. Explicit API/UI integration and live quality remain pending.

1. Add a separate learner-owned visual-generation request record with unique owner/
   request identity and canonical input fingerprint. Persist the exact target binding,
   prompt identity, state, attempt budget, timestamps, model-call reference(s), result
   version reference and non-content error code. Cover learner wipe/private recovery
   and table inventory. Do not store raw source snapshots in learner backup by accident.
2. Atomically reserve before inference. A duplicate with the same fingerprint reads
   the existing request; a changed fingerprint conflicts. Pending, cancelled, failed
   or interrupted requests never silently restart. An explicit new generation uses a
   new identity. Reconcile abandoned requests on process restart without inference.
3. Resolve answer/source currency and current trust before sending content. Use the
   normal ContextPacket/data boundary and existing FORMAT task through the gateway,
   with verified local transport. Bind output to server provenance, not model-supplied
   hashes, owner IDs or origin. Never send third-party/mixed/unknown material externally.
4. Use a bounded graph-only output schema: labels, explanations, relationships and
   text equivalent; no executable content. Enforce a single total repair/attempt budget
   across fallback and renderer failure, rather than multiplying retries by provider.
   Gateway calls already log model attempts; cancellation must stop new attempts.
5. Revalidate after inference and save the immutable visual version plus terminal
   request result atomically. Save model/prompt origin from verified call records.
   Changed/deleted answer, cancelled request or learner wipe cannot resurrect content.
   Completed retry returns the stored result, never another model call.
6. Expose explicit start/status/cancel APIs; the UI offers one Generate visual action,
   progress, stop/recovery, inline rendering/text, exact-version review and source
   access. Changing answers/unmounting cannot apply stale results. No auto-generation
   on load or failed rendering. Preserve the full explanation and follow-up form.
7. Test duplicate start, cancellation/save races, restart, source changes, wipe,
   malformed/injected graphs and hosted transport denial with fake providers before
   local synthetic quality trials. Then real sandbox keyboard/narrow/zoom/fallback
   journeys. Schema validity and owner review never certify factual correctness.

The request lifecycle is implementation work within the accepted visual lifecycle,
not new authority for public exports, hosted calls or assessment writes. G4 remains
open, including conceptual quality, original explanation generation and user review.

## Verification

Target route tests compare exact server bindings, observe changed answer hashes,
check unknown legacy lineage, source IDs, owner isolation and no model/learning writes.
Final suite and review evidence is recorded below.

Verification completed: 1512 backend tests passed (3 warnings); 10 focused target/
history tests pass. make gen-api and make lint pass. Bounded code/provenance review
found no blockers or majors and confirmed the request-lifecycle plan; reviewer did
not rerun tests. No browser claim is made for this endpoint-only change. Existing
hosted CI billing blocker is not represented as a passing CI run.
