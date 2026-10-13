# Local transfer grader evaluation — 2026-10-13

## Decision
Reject the prompt/output-budget experiment. Runtime grader, prompt version and routing remain unchanged. Valid JSON and passing software tests are not evidence of correct assessment.

## Protocol and evidence
Four project-authored synthetic responses to the reviewed training/held-out imputation task: correct, misconception, partial and instruction injection. Exercised production `Grader._llm_grade` through a gateway pinned to local `gemma3-12b`, with hosted providers disabled, zero hosted budget and a disposable database/session. Production routing, assessment submission and live learning evidence were not exercised. No paid calls or live learner writes.

Baseline rejected all four outputs. A diagnostic showed abbreviated criterion identities instead of required verbatim descriptions. An exact-copy prompt improved identity compliance but two outputs remained unusable; one recorded output-token exhaustion. Increasing the bounded output allowance produced usable outputs, but wrongly passed reuse of a median fitted on training AND held-out data. Explicit all-requirements wording did not correct that false positive.

Final sample: correct 4/4 expected decisions; misconception 3/4 (incorrect pass on reuse of the training-only parameter); partial 4/4; injection 4/4. Latencies respectively 16.52, 38.40, 13.07 and 19.14 seconds. These four cases are diagnostic evidence, not an accuracy estimate or latency benchmark. Feedback also described an explicit false fairness/accuracy claim as missing discussion, weakening corrective guidance.

## Verification and limits
The experimental code passed 1636 backend tests with three warnings; this did not catch model semantic failure. Experimental runtime/test edits were restored to the previously verified HEAD; the rejected prompt and patch are retained privately with raw results. Existing strict criterion validation is not weakened. No UI change, so no new visual, keyboard or responsive claims. The initial invalid-session diagnostic is excluded from quality evidence.

Latest sanitized CI run 38456160636 did not start its required gate due to account billing/spending-limit restrictions; runtime jobs were skipped. This is not a code-test failure or a passing CI gate.

## Next bounded step
Compare an already available local model on the same four cases before changing routing, then extend contrastive cases and repeatability checks for any promising candidate. Separate criterion identity transport from semantic correctness; do not add task-specific phrase matching or award evidence from this evaluation. Current grader quality remains unresolved, and this rollback does not prove the baseline reliable.

## Follow-up: installed 27B baseline
Gemma3-27B (installed Ollama tag, GPU) was tested on the same four synthetic responses through the unchanged v1/600-token runtime on 2026-10-13. All four returned no accepted grade: correct45.50s, misconception24.97s, partial22.49s, injection18.50s. No exceptions were exposed to this harness. These null results do not distinguish transport/schema failure from criterion validation; no raw-output diagnosis was run for this comparison. They cannot support a semantic accuracy claim. The run ended normally, with no hosted calls or production routing changes.

The bounded comparison stops here. Increasing model size alone is not an evidenced remedy. Next implementation candidate is an isolated, versioned criterion-ID output contract that preserves exact server-owned rubric text, with fail-closed unknown/duplicate/missing IDs and unchanged learner evidence rules. Document and review that contract before runtime edits; then evaluate semantic correctness separately using these cases and contrastive qualifications. Do not weaken validation or adopt the rejected prompt based on this result.
