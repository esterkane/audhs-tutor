# G2c — Ask with explicitly selected local passages

## Scope and contract

Ask previously generated without passages; source review was available only afterward.
The learner can now attach up to six local passages before asking, view the exact
snapshots afterward and follow up without changing a learning session. Existing
search, source-status, saved-answer, recovery and local provider boundaries are reused.
No dependency, database migration, mastery, assessment or scheduling change.
Mode/energy are unchanged; no automatic source selection or external request.

Inputs: bounded passage IDs and SHA256 hashes of displayed text, plus the existing
question/area/parent. Source trust and displayed-text bindings are rechecked before
claiming the request or invoking the model. A missing/excluded/changed/oversized
selection is rejected, never silently omitted. Total source text and labels are
limited to16,000 characters. Plain no-source requests preserve historical fingerprints.

Outputs: streamed explanation and an immutable completed-answer record containing
selected source text, hashes, document/version identities, provenance/location,
model/prompt versions and bounded prior-reply snapshots. The prior three answers
remain unverified conversation context; their sources are NOT automatically reattached.
A new follow-up displays that boundary; fresh evidence requires explicit selection.
Previous ancestry beyond the bound is still dropped/disclosed by the existing trace;
this is not the complete transitive origin/export eligibility implementation.

Local source selection is logged with explicit-selection mode and no fabricated
search scores, linked to the tutor/model trace in the atomic answer transaction.
No learning events are emitted. Existing provider guards deny hosted inference,
including repairs/fallbacks. A generated/paraphrased answer does not acquire owner
rights. Unknown and source-derived content remains local.

## Presentation and reliability

- Optional disclosure beside the composer; native labelled input/checkboxes/buttons.
  Enter in source search searches, rather than submitting the question.
- Selected passages and question survive browser reload; failed browser writes use
  the existing in-tab draft fallback and warning. Unreadable selection blocks send
  with an explicit recovery action. No model call while typing/searching/selecting.
- Submit locks before asynchronous hashing. Stop during hashing prevents both claim
  preparation and POST; Stop after sending retains existing uncertain-request recovery.
- Completed answers expose historical supplied passages. Existing saved-answer
  source status detects missing/changed text/newer local versions.
- Citations use `[source:S1]`. Unknown IDs in that syntax prevent completed save;
  streamed preview stays unverified. This checks IDs, not entailment, factual accuracy,
  missing citations, arbitrary links or alternative citation formats.
- No claim that selected sources support every generated sentence. Existing explicit
  per-claim local review remains separate and fallible.

## Verification and review

- Backend contracts: source snapshots/escaping, exact hashes, missing provenance,
  trust/quarantine, input bounds, unknown citation IDs, unchanged replay despite later
  edits, bounded follow-up lineage, no Session writes, legacy fingerprints, HTTP
  selected-source submission/current status and linked explicit-selection trace.
- Ten Ask browser journeys passed, then attachment flow also passed at1280px
  (390px repeated after parameterization). Includes reload, keyboard selection,
  duplicate submit, denied storage, stopped/partial requests and selected-source UI.
  A deferred digest regression proves Stop before hashing completes sends no request.
  Desktop/narrow screenshots inspected; existing design tokens/components retained.
- Targeted frontend recovery/catalog tests:7 pass. TypeScript/ESLint/build pass;
  production build retains the existing chunk-size warning. Backend mypy from its
  configured working directory passes245 files; running it from the repository root
  omitted its config and produced unrelated diagnostics, not a code regression.
- Code/pedagogy review found the pre-hashing Stop gap; fixed and regression-tested.
  Recheck reported no remaining blockers. Broad human/assistive-technology acceptance
  and owner-reviewed factual-quality acceptance remain open.

## Real local-model observations (synthetic only)

Temporary isolated SQLite DB, llama31-8b through the ordinary gateway, budget zero,
only loopback Ollama configured. No hosted judge or owner/course content used.
Three cases: byte-storage calculation, conflicting record counts, unrelated passage
containing an instruction injection. Iterations exposed missing source-basis disclosure,
inconsistent citation syntax and a late-system-message formatting artefact; the final
packet uses versioned task and response-contract files with a final user request.

Local-only three-case outputs are in `evals/results/ask-selected-sources-20261012.json`
(private archive only; raw evaluation results are excluded from the sanitized variant):
2.92/3.43/3.34seconds total completion. Arithmetic was correct (1,000bytes), conflict
was identified, and irrelevant poisoned material was ignored/disclosed. A final
conflict-only prompt refinement completed in1.52seconds but still invented “another
part of the study.” That is an unresolved factual defect, not a passing quality gate.
These tiny warm local samples are not a latency benchmark or proof of general accuracy.
They justify retaining unverified labels and the explicit source-review workflow.
The existing session-tutor eval runner does not exercise Ask; this isolated sample
invoked the actual Ask service instead. No paid rubric judge ran.

## Remaining G2 work

Safe inspected external source snapshots, broader reference coverage, direct navigation
from claim markers to passages, stronger conflict/unsupported-inference evaluations,
and an owner-reviewed cross-area question set remain open. G2 is not complete.
Do not promote these replies into trusted reuse, public exports or mastery evidence.

Final validation: full backend1,401 tests passed with three existing dependency warnings.
After the final selection-trace/provenance additions,18 affected Ask tests passed;
these include the new HTTP source-status and trace binding assertions.
