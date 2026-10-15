# LT1: source-aware conversation brief

Status: implementation design, 2026-10-15. Opening-question retention is delivered; this document specifies the remaining context behavior. It does not certify a summary or add learning evidence.

## Concrete failure and existing boundaries

Ask carries only the opening question and three recent exchanges. A learner can introduce a useful constraint or a hypothetical dataset mid-conversation, then lose it from the model context while still seeing saved answers. Replaying the opening question cannot repair that. Replaying every answer increases cost and can reinforce earlier unsupported claims.

Existing `AskQuestion`, immutable saved-answer request/metadata, owned parent links, source snapshots and exact command receipts are sufficient for an initial bounded brief. No second memory service, database table, automatic model summary or global learner profile is required. Existing `ask_reuse.input_binding` hashes the actual packet and request; the brief must participate in both. `useAskRequestRecovery` must freeze it with the submitted question.

## Intended learner experience

The learner should not have to maintain a diary to receive coherent tutoring. The eventual brief retains relevant context with visible origin labels and lets the learner correct it. It is accessible from the current answer without becoming a compulsory setup form.

Deliver in two distinct increments:

1. **Explicit retained context:** optional learner-authored task/context, assumptions or examples, and unresolved question. Inherit from the selected parent branch. Display the exact snapshot used for the saved answer. Let the learner edit or clear context for the next reply without changing past answers. This provides control but is not the complete automatic-retention solution.
2. **Proposed context updates:** a local model may propose concise updates from bounded owned exchanges. Proposals remain unverified and must preserve exact supporting turn/source references. The learner can accept/edit/reject; regeneration must not silently change accepted context. Evaluate whether acceptance prompts create more burden than benefit before making proposals prominent. No background paid calls or automatic fact promotion.

Source-backed facts remain a separate lane: only explicitly selected current passages, verified against their displayed hashes, count as supplied source evidence. A retained note can mention an earlier claim but cannot inherit a checked badge, citation or hosted-transport permission. Tool-observed results require exact execution/file versions from existing records before they can populate a verified-result lane. Until that linkage exists, say the result is unavailable or unverified rather than reconstructing it.

## Data and request contract for increment 1

Add an optional bounded `conversation_brief` to `AskQuestion`. Use a strict versioned schema, with separate text fields for current task, retained learner notes, hypothetical assumptions/examples and unresolved question. Suggested limits: task500, notes1500, examples1000, unresolved500 characters; reject unknown keys and over-limit input. All fields are untrusted learner input, not evidence. An all-empty object explicitly clears the brief; an absent or null field means inherit and preserves legacy request fingerprints and inherits the immediate owned parent's effective brief. New-topic requests never inherit.

Record the effective snapshot, normalized hash, mode (`supplied`, `inherited`, `cleared`, `absent`), parent answer ID when inherited, and origin `learner_supplied_unverified` in answer metadata. Store the original request separately so retry fingerprints remain exact. No silent reconstruction of legacy missing/malformed metadata. Inherit only after existing owner/surface/area checks; validate the stored shape again. Return completed receipts before resolving any mutable context.

Prompt assembly includes the effective brief once in an escaped data block. System policy says: current question overrides historical context; examples are hypothetical; notes may be wrong; do not invent file inspection or calculations. Keep the opening question historical and distinct from the current task. Recent history remains bounded. Store the exact effective brief in provenance; do not put its text into telemetry labels or logs. Changed brief must invalidate exact reuse. A cleared brief must not reappear from a grandparent or opening-context metadata. Clearing retained notes does not erase historical questions/answers; disclose this distinction. Persisted snapshots require the full versioned field set, allowed mode/origin and matching hash; request defaults must not repair malformed storage.

No schema migration is intended: existing saved-answer metadata/request storage holds immutable snapshots. Verify private backup, learner deletion and export include/exclude them under existing policy; user-entered text is not automatically permission-cleared. This remains local under existing transport containment.

## Frontend behavior

Use existing Disclosure, fields, draft recovery and design tokens. Label the optional editor “Keep context for this conversation.” Explain that entries are retained learner notes, not checked facts. Prefill from the exact selected parent's snapshot only after the owned answer loads; never overwrite local unsent edits on refetch. Keep scoped draft identity per learner/parent. Distinguish no local draft from an intentionally empty edited draft. New topic resets scope.

Show a concise saved-context summary with an optional expanded snapshot; do not add four always-visible form fields above the answer. Editing affects only the next response. Stop, error, reload and route changes preserve the submitted request and independent unsent draft. Retry uses the frozen old request, even if current fields differ; disclose that existing behavior. An explicit clear action must be reversible before sending and must not delete historical answers.

## Acceptance before commit

- Legacy request serialization and receipt replay are byte/semantic compatible.
- Inheritance uses the immediate owned parent, not another branch or arbitrary metadata identity.
- Five-turn conversation keeps a middle-turn task constraint explicitly added to retained context without replaying every answer.
- Hypothetical quantities remain labeled; a later real-task question does not silently use them as measured data.
- Explicit clear stays cleared on further turns; new topic starts without context.
- Changed notes alter reuse identity; concurrent duplicate submission produces one saved reply.
- Failed source/hash/owner checks do not leak or publish a brief.
- Snapshot reflects what the model actually received; deleting a source or parent cannot cause a completed retry to regenerate.
- Keyboard, narrow viewport, reload, refetch and Stop preserve correct editable and submitted states. A cleared draft stays cleared for new submissions; an older frozen retry visibly retains its original context.
- A bounded local-model sample tests confusion repair and example/fact separation; API/UI fixtures alone cannot establish this behavior.
- No competency, FSRS, grading, source permission or model routing changes.

Likely files: `backend/app/schemas/ask.py`, `backend/app/orchestrator/ask.py`, a small context helper if assembly needs separation, their tests, `frontend/src/routes/Ask.tsx`, existing Ask context disclosure, one optional brief editor, API generated types and Ask journeys. Do not modify lesson/session logic or unrelated screens.

## Later work and limits

Increment1 does not implement local proposal generation, automatic source/tool-result retention, conflict resolution across revisions or full LT1. Those require review of exact citation/lineage and correction behavior before implementation. LT2 guided mode remains explicit choice; LT3 teaching response quality and LT5 human transfer remain separate gates. The instructional-design quality supplement applies: diagnose the actual problem, preserve evidence boundaries, and test correctness separately from output completeness.

## Implementation checkpoint — in progress

Backend draft exists in `schemas/ask.py`, new `orchestrator/ask_brief.py` and Ask assembly/storage. Optional request serialization retains legacy omission; effective context inherits from the immediate owned parent, clear persists, and malformed persisted snapshots fail closed. An explicit clear removes retained notes, not historical exchanges. 39 affected backend tests pass after strict snapshot validation; 14 brief-contract tests also pass, including the added null/malformed-envelope cases. Targeted Ruff and whitespace checks pass. Code/pedagogy design review found no fundamental blocker; requirements for strict persisted validation, null semantics, recovery validation and explicit-vs-automatic retention were incorporated.

Not ready for commit/publication: frontend editor and truthful saved-brief disclosure, frozen recovery-body validation, generated API types, prompt-version tagging, metadata/reuse/branch/privacy edge cases, local-model sample, browser/keyboard/narrow checks and final implementation reviews remain. No user-visible editor yet; do not describe this as delivered memory. Preserve inherited acquisition/source-registry/eval work. Batch this design with the verified implementation in both repositories.

### Editor checkpoint — 2026-10-15

Optional editor, scoped JSON draft, clear/undo, saved-context display, frozen-retry brief validation and generated API types are implemented but uncommitted. Code review identified and resolved consumed-new-topic draft retention and client/server hash-validation mismatch. Frontend now checks the complete envelope and SHA-256 before prefill/display; stale async checks cannot cross metadata identities. Consumed drafts clear only when unchanged relative to the submitted snapshot.

49 affected backend tests, five UI tests, targeted lint/mypy, TypeScript and production build pass. Existing bundle-size warning remains. Current corrected browser run is pending (log `/tmp/brief-browser-v2.log`, exec session37413); do not restart without checking its state. First browser attempt included intermediate fixture/hash and nullable-state mistakes, fixed before rerun. Remaining: inspect corrected browser screenshots, add direct new-topic-after-success regression, complete recovery/branch/reuse edge checks and local-model/pedagogy acceptance, then dual publication. No live DB changes or hosted calls.

Browser update: session37413 finished with two failures while refilling the task field after interrupted streaming. Trace pinpointed label lookup after controlled-textarea editing. Changed editor to explicit sibling label/textarea `htmlFor`/`id` associations. Corrected rerun is session91541, `/tmp/brief-browser-v3.log`, max-failures1. Do not claim browser acceptance yet. Both code-review majors cleared on follow-up review; no further code blockers reported. Production build passes. Five UI tests include canonical-hash rejection.


## Final increment 1 acceptance

Explicit retained notes are implemented. 59 affected backend tests, five component tests, 20 Ask browser journeys, targeted Ruff/ESLint/mypy, TypeScript and production build pass. Browser tests cover clear/undo, edited notes after interrupted generation, exact frozen retry, reload, inherited notes and fresh topic at390/1280px. Explicit label associations fixed the controlled-textarea browser failure. Both final screenshots inspected for wrapping and visible focus. Code and pedagogy reviewers cleared the bounded context controls; source reviews do not substitute for the tests. Existing bundle-size warning remains.

A two-turn synthetic actual Ask responder sample used installed local llama31-8b in a disposable database with hosted keys disabled and zero hosted budget. Turn1 correctly separated the invented salary from file evidence. Turn2 failed teaching quality: it treated raw coefficients as feature importance without scaling/model qualifications and ranked0.2 above0.3. Wall times were8.86s and7.33s, not a latency benchmark. Record this as a major unresolved LT3 teaching issue, not a context-control failure or a model-quality pass. Do not change routing or claim improved learning from this sample. Private runner/raw evidence retained separately.

Increment1 is complete as an optional explicit context control. Full LT1 still requires source-linked low-burden proposals and trustworthy tool-result context; manual notes do not substitute for those. Next bounded work: capture the coefficient/importance failure as an evaluation case and address explanation correctness alongside explicit LT2 guided choice. Human comprehension, screen-reader acceptance and general multi-turn quality remain unverified. No mastery/scheduling/source-permission changes.

Remaining increment 2 is specified in [Reviewable context proposals](ASK-CONTEXT-PROPOSALS.md), including acceptance provenance through edits/inheritance and receipt lifecycle evidence. Proposal generation/review UI are not implemented.
