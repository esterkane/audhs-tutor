# LT1 increment 2: reviewable context proposals

Status: implementation specification, 2026-10-15. Not implemented or enabled. Complements the delivered explicit conversation brief; does not replace it or resolve the open teaching-quality gate.

## Problem confirmed in current code

`orchestrator/ask.py` loads a bounded parent chain, opening question and accepted brief. `ConversationBriefEditor` requires the learner to write four optional fields manually. Useful constraints in middle turns can therefore disappear unless the learner maintains those notes. Sending all old answers would retain unsupported claims and increase latency.

The existing brief is a string-only version-1 object. Its saved origin is learner-supplied and unverified. Copying a generated summary into it without recording provenance would falsely attribute model wording to the learner and erase the supporting turn/source identity. The proposal and acceptance path needs an explicit origin contract before UI integration.

## Experience and scope

Add an optional **Suggest notes from this conversation** action inside the existing context disclosure. No modal, prompt after every answer, automatic inference or compulsory review. Show progress and Stop; the question and current notes remain editable. Failure leaves those drafts intact. Avoid making suggestions more prominent until real learner testing shows they reduce effort.

Show each proposed field next to the current value, with its supporting turn references and visible origin: learner statement, hypothetical example, unverified tutor claim, or selected source passage. Offer **Use selected changes**, **Edit**, and **Dismiss**. Nothing selected by default; acceptance affects the next reply only. Preserve rejected/unchanged fields and offer Undo before sending. A learner edit to model wording remains learner-edited/model-originated context, not checked fact.

Generation and acceptance are separate. If the parent branch, current notes or selected passages change while generation runs, retain the result as a stale preview; never overwrite newer work. Let the learner request a fresh proposal. Accepting a stale preview is disabled. Stop/reload must use a durable request identity; no automatic repeat inference after an uncertain outcome.

## Request and provenance contract

Use a new strict request schema in `schemas/ask_context_proposals.py`, separate from the existing AskQuestion version. Bind to owned parent answer, area, canonical hash of the effective current brief, explicit selected passage IDs/hashes, and an operation-tagged request identity. No arbitrary client-supplied history or tool results.

The request includes the complete bounded unsent brief draft, because saved parent notes do not represent current composer edits. The server computes its canonical hash; a client hash alone is not trusted. Bind generation to that exact snapshot and acceptance to the same base snapshot, rejecting changes rather than merging silently. Resolve inherited provenance server-side; supplied text is not proof of independent authorship. Domain-separate both request fingerprints and response envelopes for `context_proposal.v1` and `context_acceptance.v1`; existing AskRequest has no operation column, so enforce operation identity before replay parsing.

Resolve at most three owned ancestor exchanges plus the validated opening question and current brief, following the existing branch checks. Bound aggregate input before inference; reject oversized input with an actionable message rather than silently dropping supporting content. Avoid duplicate opening turns. Show that proposals cover only the supplied portion of the conversation; do not advertise comprehensive memory.

Proposal v1 contains at most four field replacements, one per existing field, respecting its existing length limit. Each replacement carries a nonempty rationale and bounded supporting references. References identify the exact saved answer/turn and role (learner question or tutor reply), or explicitly selected passage/version. Include canonical text hashes and exact substring offsets; the server validates ranges against the precise original text. Text matching establishes attribution, not truth or entailment. Source material remains untrusted and local.

Do not serialize raw source passages into accepted-note provenance. Store reference IDs, version/hash and offsets; display the original passage only after an owned, current lookup. Missing/changed content is shown as unavailable/stale. A persisted generated paraphrase is derived content and retains source restrictions even after editing or accepting it. Unknown lineage stays local and excluded from public exports. Owner acceptance does not grant hosted/public permission.

The generator cannot assert verified execution, mastery, correctness or source permission. A hypothetical must stay labeled hypothetical. A tutor answer must stay labeled unverified even when the learner accepts its summary. A source citation does not prove the proposed paraphrase is supported. Do not add a tool-result lane until an existing immutable execution record can be bound and checked.

## Persistence and integration decision

Investigate reuse of the existing operation-tagged AskRequest receipt rather than creating a second answer or memory service. A proposal is not a TutorAnswer and must not appear as a searchable teaching answer. Completed receipt replay precedes mutable source lookup, returning the historical proposal with current availability checked separately. An unresolved receipt cannot be silently taken over.

Before implementation, prove that proposal receipts and accepted provenance are handled by learner export, wipe, private backup and sanitized-export rules. Current schema inspection alone does not prove those paths. If a new durable table or altered retention is necessary, document the change and obtain any required lifecycle decision before migrating.

Keep the existing ConversationBrief v1 intact for legacy requests. Design an optional versioned acceptance envelope alongside it, binding the accepted field values, proposal receipt, origin and reference hashes. Never trust client-supplied provenance: the server resolves the owned proposal, verifies unchanged base context and selected field values, and records which values were edited. Explicit learner-only notes retain their current behavior. Acceptance must participate in reuse identity and frozen retries. Neither accepting nor dismissing proposals changes grading, competency, FSRS or session plans.

Accepted provenance must survive inheritance and subsequent manual editing. Track retained claims/spans where possible; if an edit prevents exact attribution, label the entire affected field mixed/model-derived and retain the union of its source restrictions. Do not let the legacy manual-editor path relabel inherited generated wording as learner-only. Clearing a field removes its content; replacing it establishes learner-only origin only when independently supplied authorship is established, never merely because the learner typed or accepted a paraphrase. Unknown lineage remains visible and restricted. Test mixed learner/source/tutor content within one field, partial edits, inherited unedited fields and explicit clearing.

## Local generation boundary

Use the established ModelGateway with explicit local-only containment. No automatic hosted fallback, even if the registry assignment is hosted or a local response fails. Course-derived history is not covered by the pending synthetic hosted comparison approval. Proposal generation must not change the current response mode or model assignments.

Run one bounded local synthetic sample only after deterministic contracts pass: preserving a middle-turn constraint, keeping an invented dataset hypothetical, and rejecting an unsupported claim promoted from tutor output. Failure keeps the feature unshipped; schema validity and quote matching alone cannot pass semantic acceptance. Do not begin another open-ended prompt sweep.

## Ordered implementation slices

1. **Provenance and lifecycle:** validate the receipt/export/wipe behavior; implement strict proposal/reference contracts and ownership/hash/offset validation. No UI exposure or inference yet.
2. **Local proposal service:** bounded packet construction, durable replay, local-only route, failure preservation and source/reference binding. Record exact synthetic correctness evidence separately from contract tests.
3. **Review and acceptance:** optional disclosure, field comparison, explicit selection, edit/dismiss/Undo, stale-proposal protection and accepted-origin envelope. Preserve question drafts and current context.
4. **End-to-end acceptance:** inspect desktop/narrow UI and keyboard behavior; simulate interrupted generation, changed notes, new branch, changed/deleted source, reload and duplicate acceptance. Human testing must assess whether review effort is lower than manual note-taking before broader prominence.

Likely files: a new context-proposal schema/service and tests; `api/ask.py`; existing context editor/draft helpers; generated API types; Ask browser journeys. Modify the main Ask responder only to consume validated accepted provenance. Preserve the pending LT2 diff; no unrelated screen or learning-logic changes.

## Required failure fixtures

| Scenario | Required result |
| --- | --- |
| Tutor invented a salary; learner later asks about a real dataset | Example stays hypothetical; no file-inspection claim |
| Learner corrects a constraint | Show explicit proposed replacement with both turns; no silent overwrite |
| Relevant passage changed after preview | Acceptance blocked; current notes preserved |
| Another learner/branch reference supplied | Reject before inference or disclosure |
| Notes edited while response arrives | Stale preview; no draft loss |
| Stop after dispatch, then reload | Recover receipt status; no duplicate inference |
| Model quotes correct words but changes their meaning | Binding may pass; semantic acceptance fails |
| Hosted assignment or local failure | No external transport |
| Saved source removed after completion | Historical receipt retained; source unavailable, never reconstructed |
| Clear notes or start new topic | Old accepted context is not resurrected |

## Lifecycle evidence from the existing implementation

Three targeted tests pass: owned completed/pending request export and wipe (other learner preserved), and exact synthetic proposal-shaped receipt roundtrips through both learner and full backup scopes without adding a TutorAnswer. Targeted Ruff passes. These prove existing receipt storage behavior, not an implemented proposal service or public-export eligibility. Existing raw receipt content is copied by backup; therefore the proposed receipt must itself omit raw source snapshots. No live database or model calls were used.

## Reference-contract foundation — 2026-10-15

Implemented isolated strict proposal/reference schemas and pure binding validation in `schemas/ask_context_proposals.py` and `orchestrator/ask_context_binding.py`. Rejects duplicate fields/references, excessive lengths, unknown inputs, changed hashes, invalid/whitespace ranges and coerced version/offset types. Offsets use original Python Unicode code points; they are not JavaScript UTF-16 indexes. An empty changes list represents no useful suggestion.

15 offline tests, targeted Ruff and strict mypy pass. Code review found no blockers and clarified that the service must retain the server-resolved input map (record/version/origin) alongside references in durable receipts. The helper returns a detached validated proposal but does not certify meaning, ownership, branch, permissions or full provenance. A deliberate meaning-changing paraphrase test demonstrates this limit. No API, UI, provider, storage or learning-state behavior changed; no browser/model tests are implied.

Next: implement owned bounded input resolution and durable proposal receipt envelopes, preserving unsent draft identity and provenance. The new types are not an enabled feature and do not complete increment2.

## Owned recent-input resolver — 2026-10-15

`ask_context_inputs.resolve` now reads up to three owned Ask ancestor turns, rejects area conflicts, malformed/cyclic links and unavailable turns, captures exact unsent notes, and uses the existing explicit source/hash/trust resolver. Input text plus serialized notes is capped at24000 characters, without truncation. It does not resolve an opening question beyond this window yet; `older_history_omitted` makes that limit explicit. No implicit source reuse, generation, API exposure or learning writes.

Review identified blank parent IDs bypassing the lookup and mutated brief models bypassing field validation; both are rejected at entry, and source selections are revalidated. Tests cover branch isolation, ownership/surface, invalid links, cycles, area conflicts, oversized input, changed sources, missing parent identity and mutated notes. Alongside reference-binding tests,27 tests pass, targeted Ruff and strict mypy pass. Ownership is scoped to conversation rows; corpus source eligibility follows existing shared-corpus policy, not a new per-document ownership claim.

Remaining before service integration: validate/bind opening context, retain exact record/version/origin maps in durable receipts, inherited accepted-note restrictions, local-only generation and explicit acceptance/UI gates. No semantic-quality or full feature-completion claim.


## Durable proposal receipts — 2026-10-15

Added an internal operation-separated receipt layer using existing AskRequest storage. Completion binds learner, request fingerprint, parent, area, unsent brief hash and selected source hashes; an atomic pending-only update prevents overwrite. Receipts retain every input record/version/origin and text hash, including unquoted influences, without raw input snapshots. Historical replay survives parent removal. Local-only/public-export restrictions are policy labels, not proof of transport or semantic correctness; future callers must enforce them. No generation, endpoint, acceptance or learning-state changes.

Verification: 33 combined receipt/input/binding tests passed, followed by all seven receipt tests after adding an independent-session race. Targeted Ruff and mypy passed; bounded code review found no blockers. Tests exposed JSON null versus SQL NULL pending storage and the guard now handles both. Rollback leaves the original claim pending; two competing completions preserve exactly one result. No browser checks apply to this unexposed helper. Opening-context binding, local service, inherited restrictions and review/acceptance UI remain open.


## Opening context and coverage — 2026-10-15

The proposal resolver now retains the original question outside the three-exchange window using the saved conversation identity and the existing Ask root lookup contract. It validates owner, Ask surface, root status, area and nonblank bounded question; it does not include the old tutor answer. Opening input carries the exact record/hash and counts toward the aggregate limit. Invalid/unavailable openings are omitted with an explicit flag. This relies on saved conversation identity, not independent traversal of every omitted ancestor.

Receipts now preserve recent-turn count, older-history omission and opening availability so historical replay cannot imply complete memory. This internal unreleased envelope has no live generated receipts to migrate. Verification:40 combined input/binding/receipt tests passed before the coverage fields; seven receipt tests passed afterward, with targeted Ruff/mypy. Bounded code review found no blockers in opening lookup. No model calls, UI changes or learning-state changes. Local generation, accepted-note lineage and review/acceptance UI remain next.


## Local service candidate — 2026-10-15 (uncommitted, unexposed)

Internal suggest service uses durable claim/replay, the gateway's fail-closed transport checks and an atomic proposal/trace commit. Four fake-provider tests pass: historical replay despite deleted parent/changed source, invalid attribution with no automatic repeat, trace-save rollback preserving the model-call record, and transport denial before sending. Ruff/mypy pass. Code/pedagogy review found no blocker for an unexposed candidate; this is not semantic acceptance or a complete Stop/retry journey.

A four-case synthetic direct local sample with gemma3:12b used the exact candidate prompt/schema, one attempt per case, no repairs, no live DB or paid calls. Model digest, prompt hash, inputs, output and timings are retained privately. Correction and no-useful-notes cases bind; false-claim and hypothetical cases invent out-of-range offsets. The false-claim output also replaces an attributed false belief with an unsupported “may improve fairness” assertion. The hypothetical output retains an invented-example label but loses the actual example details. Times:15.12s,7.93s,7.20s,2.05s; four samples do not establish general latency. No feature exposure or routing change follows.

Next corrective design: keep the durable exact-reference contract, but have structured generation select server-provided bounded input identifiers and let deterministic code construct whole-input ranges/hashes. This avoids asking a language model to count Unicode offsets; it does not establish entailment or cure false-claim laundering. Retain the false-claim/correction/hypothetical/no-change cases and add unrelated-reference semantic review. Do not repeat a prompt-only model sweep.

Separately, inspection found that gateway.complete has no cancellation-accounting branch around provider.complete (streaming has one). Before a Stop control is exposed, reproduce and address this shared boundary in its own bounded change; durable pending claims prevent resend but do not themselves account for interrupted inference. Concurrent service dispatch and cancellation tests remain required before UI integration. Accepted-note lineage and edit restrictions remain open.


## Deterministic selection candidate — 2026-10-15 (uncommitted)

Generation now selects input IDs; the server constructs full-input Unicode ranges and hashes through the existing receipt contract. Unknown/duplicate selections, empty inputs, mutated models and excessive size are rejected. Whole-input references are attribution, not precise evidence excerpts or semantic support. The service also removes unchanged field values after validation, so empty no-op suggestions do not create review work.51 focused tests passed before duplicate-request/no-op service additions; the latest13 selection/service tests cover those additions. Ruff/mypy and bounded structural review pass.

One fixed four-case local comparison per model, with no repairs, tested the new representation. Both Gemma12 and Gemma27 produced four bindable selections; neither passes semantic release. Gemma12 still weakens/misattributes the false claim, loses hypothetical example details and misdescribes a correction as a combination; its no-op is now removed by deterministic service filtering. Gemma27 preserves false-claim attribution and the invented example, but invents an unresolved agenda to confirm learner understanding in the correction case. Independent pedagogy review rejects release. Generation times were5.09/5.05/4.33/3.86s (12b),22.91/17.18/13.63/4.46s (27b); these are individual direct-provider samples, not full service latency or general performance evidence. Exact model digests/input/output/prompt hashes retained privately. No routing change, UI exposure, paid calls or additional sweep.

The remaining problem is faithful selection of learner intent, not reference formatting. Do not infer semantic validity from this structural improvement. Preserve these cases for the next explicit evaluation design; Stop cancellation accounting is being fixed independently in the shared gateway.
