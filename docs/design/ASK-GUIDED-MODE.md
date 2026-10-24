# LT2: explicit Ask teaching choice

Implementation plan2026-10-15. Existing Ask has explicit explanation prompts and no saved mode; requests for guided dialogue are not represented as a durable choice. Existing 20 Ask browser journeys passed on the unchanged starting implementation; no additional baseline run is needed to prove the missing schema/UI field.

Add optional `teaching_mode: explicit | guided` to Ask requests. Omitted/null inherits the immediate owned parent's recorded effective mode; no parent, legacy or invalid stored mode defaults to explicit. Omitted fields remain omitted from serialization so old receipts still replay. Persist effective mode on each answer. The actual mode-specific prompt participates in exact reuse identity. Existing completed receipts return before mutable lookup; retry retains the original mode.

UI offers Direct explanation (default) and Learn together with a concise consequence description. The next answer inherits the selected parent mode, while a new topic starts explicit. Changes affect only the next reply, not saved responses. A visible Explain instead action selects explicit without sending automatically or destroying a draft; if empty, provide an editable direct-explanation request. Saved replies label their recorded mode; legacy mode is not falsely reconstructed for historical display. Invalid recovered requests must not silently become guided.

Guided policy: first address the learner's reasoning, teach the needed distinction with enough context, then ask at most one purposeful question. If confused, explain the missing prerequisite before asking more. Direct requests and stop/change-topic remain respected. No confidence gate, praise template, mandatory assessment, mastery or FSRS writes. This is a teaching preference, not permission to invent evidence. Current source/citation rules and local-first containment remain intact.

Files expected: Ask schema/orchestrator, a guided task prompt, composer and saved mode display, retry validation/generated types, targeted API/UI/browser tests. Do not change lesson/session/grader prompts.

Acceptance: default and explicit override; inherited guided across more than three turns; branch/new-topic separation; old-mode display; frozen retry after changing preference; exact reuse incompatible across modes; owner/area boundaries retained; keyboard and narrow layout; local guided/explicit samples assessed separately from storage. Explicit mode does not fix the existing coefficient-importance failure. LT3 semantic quality and LT1 automatic context proposals remain open.

## Verification checkpoint — 2026-10-15

Implementation is local and uncommitted. Backend and UI support explicit/guided
choice, immediate-parent inheritance, branch-local drafts, recorded-mode labels,
Explain instead without automatic submission, and frozen retries. Invalid saved
mode data defaults safely to explicit. No learning decisions or scheduling change.

- 66 affected backend tests pass (Ask, sources, reuse, opening context, retained
  brief and teaching mode). Cross-mode saved-answer reuse is rejected.
- TypeScript, targeted ESLint/Ruff and production build pass. Existing large-bundle
  warning remains.
- Two Chromium journeys pass at 390 and 1280 pixels: keyboard choice, partial reply,
  changed choice, reload, exact retry, saved-mode label and draft-preserving direct
  explanation. Both screenshots inspected; no horizontal overflow. Native select
  ArrowDown behavior also failed in isolated plain HTML on this setup; keyboard
  type-ahead plus Enter works and is exercised. All 22 Ask browser journeys subsequently passed. Twelve related UI/retry unit tests also pass.
- Bounded independent code and pedagogy reviews found no blockers/majors. Minor
  inserted-question wording changed to “no question needed.”

### Local teaching sample: quality gate not passed

Three synthetic requests ran locally against llama31-8b in a disposable database;
no hosted calls, personal data or course text. Model digest was recorded before
inference; seed was not fixed. Raw artifacts remain private. This is a diagnostic,
not a comparative benchmark or evidence of learning efficacy.

1. Direct explanation of training-only median fitting omitted the leakage rationale,
   claimed improved prediction accuracy without evidence, and introduced an
   irrelevant new student into its example. Semantic failure despite direct style.
2. Guided reasoning about using all rows without labels supplied a generic median
   explanation and endorsed using all rows, then asked one question. The question
   lacked explicit held-out context; this limits interpretation as a leakage test.
   The response nevertheless did not resolve that consequential ambiguity.
3. “I am lost; no questions yet” with explicit training/held-out history restored the
   task and did not ask a question. It retained training-only fitting, but incorrectly
   implied evaluation requires a dataset with missing ages. Partial behavior pass,
   not a factual-quality pass.

Do not declare Learn Together quality-ready from interaction tests. Next: inspect
these failures with exact task context and selected factual evidence, before a
bounded corrective change. Do not add broad prompt rules or switch providers based
on three outputs. The existing coefficient-importance failure also remains open.
Publication and integrated acceptance remain pending.

### Matched-context follow-up

A second bounded diagnostic used the identical, explicit training/held-out question
in direct and guided modes, identifying age as an input feature. Both responses
still endorsed fitting on both sets. Direct mode invented unavailable observed
ages in an all-missing evaluation example and gave incorrect median arithmetic.
Guided mode suggested fitting separate medians per set, gave incorrect arithmetic,
and asked about multiple missing ages in one row despite the single-feature task.
This removes the first guided fixture's ambiguity as the sole explanation. Both
modes fail semantic acceptance. No further prompt-only retries were run.

Recommended next bounded test: attach an explicit, versioned factual passage and
run the same two requests through the existing grounded Ask path. This will
separate a retrieval/context gap from failure to follow supplied evidence. If it
still fails, evaluate an already-installed stronger local model on these fixtures
before considering any routing change. Keep mode behavior and factual accuracy as
separate outcomes; no paid model or automatic assessment is authorized here.

### Grounded comparison and navigation follow-up

The two matched requests were repeated through the existing source-selection path
with one versioned synthetic reference, a frozen passage hash and a worked example.
Both local llama31-8b replies now prescribed fitting on observed training ages only
and using the same median for both sets, with correct example values and source
citations. The guided answer did not ask a question (allowed by the at-most-one
contract). This is narrow source-adherence evidence, not automatic verification or
proof that unrelated sources and unsourced answers are reliable.

A further browser regression passed: legacy answers show mode not recorded; a
completed guided choice survives reload and a follow-up; starting a new topic
returns to direct explanation. Total verified Ask journeys now 23 (22-suite run
plus this additional case). No application changes followed those runs.

The same two unsourced requests completed with already-installed local Gemma3-12b,
with its digest captured before inference. Both endorsed combining training and
held-out ages. The guided reply also reported the median of seven sorted values
[25, 28, 30, 32, 35, 40, 42] as 30 instead of 32. No production routing change was
made: the larger candidate does not resolve this failure. No further model sweep
is justified by this bounded result.

### Next implementation boundary

Prioritize evidence selection and claim checking using the existing grounded Ask
and answer-check interfaces. Before adding automatic retrieval, inspect source
ownership/permission constraints and present the proposed source set for learner
review; do not silently attach private materials or treat saved model prose as a
trusted source. Retain exact passage versions and invalidate checks when the answer
or source changes. A supporting citation must not become a correctness badge.
Use the matched failing question plus changed-source and irrelevant-source controls
for acceptance. This is the next investigation boundary, not an approved change to
source-selection semantics. LT2 publication remains pending its teaching gate.

### Existing checker diagnostic

Two local checks of the same observed false answer against the synthetic reference
were rejected by exact answer/passage binding; no check receipt was saved. The
first diagnostic omitted the returned proposal, so the diagnostic gateway now
retains the returned provider result (excluding raw transport payloads) before
application binding checks. Two offline diagnostic tests and targeted Ruff pass.

The recorded second proposal shows the concrete issue: it labels the wrong
combine-both-sets claim supported while quoting a training-only rule; quotes text
from the answer as if it came from the source; and quotes source statements as if
they were claims in the answer. Thus this is a semantic role-confusion failure,
not merely inconvenient strict matching. Keep exact-quotation validation intact.
Do not turn a model's unsupported approval into a verified badge.

Next bounded candidate: distinguish the answer being reviewed from admissible
source evidence in separate labeled input blocks, preserving the current schema
and binding rules. Evaluate the captured false answer, a genuinely supported
answer, and irrelevant evidence before adopting any change. Do not automatically
run checks or attach sources; learner control remains unchanged. Raw outputs stay
private; no hosted inference or routing change occurred.

### Separate answer/evidence packet candidate: rejected

Three local synthetic checks used separate answer_to_review and source_passages
messages plus explicit role/negation rules, without changing production code.
The observed false answer still received unsupported supported verdicts, including
answer text treated as evidence; exact binding rejected the result. The genuinely
supported answer and unrelated audio-source control both produced bound reviews
with the expected supported/insufficient outcome. These two controls do not offset
the failed contradiction case. Do not deploy the candidate or relax binding.

The diagnostic gateway review found no blockers but noted its standard runner
writes reports after successful respond calls. Capture in memory alone does not
ensure a failed run is persisted. The private checker runners explicitly catch
errors and write provider_responses; those artifacts do preserve these failures.
A remaining diagnostic-tool task is durable failure recording in the shared runner,
with a regression that fails after a provider result but before an answer is saved.

Stop prompt-only trials on these known cases. They demonstrate an unresolved
semantic review limitation, not a UI defect or permission blocker. Existing local
source selection and explicit model-review labeling remain in force. This does
not authorize automatic truth judgments, learning evidence or a provider switch.
