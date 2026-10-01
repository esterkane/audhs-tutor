# Quoted-feedback local diagnostic

Status: diagnostic completed; not enabled in live tutoring.

Test a structured formative-feedback contract that requires exact, bounded quotations from the current learner answer. Validate quote membership and selected explicit/Socratic mode per request, then manually inspect the model's reasoning. Keep validation distinct from truth, grade, mastery and interpretation. Use the existing accounting gateway with pinned installed local models, no hosted fallback/budget, a disposable database and synthetic material. No UI, database migration, live routing or learning-state change.

The existing free-text model sample corrected arithmetic when given local calculations, but still leaked tags and invented a fraction-format objection. Regex extraction of all possible natural-language attributions would be unreliable. This diagnostic tests a typed alternative before changing the live flow or adding inference retries to user requests.

Acceptance: reject fabricated/reworded/corrected quotes; isolate simultaneous request contracts; do not put learner text in generated schema; reject unexpected fields and extra explicit-mode question fields. Preserve actual requests, final output, prompt hash, timings and all gateway attempt outcomes. Test wrong/correct/hypothetical/incomplete/unknown-rubric/injection cases separately from the literal contract's validity. A well-formed quote cannot establish that the attached judgment is true.

## Completed diagnostic — 2026-10-01

Seven identical synthetic cases were run once per model. All 21 responses passed literal quote validation on the first gateway attempt. This establishes neither semantic correctness nor production readiness.

| Model | Median complete response | Interpretation findings |
|---|---:|---|
| Local Gemma 3 12B | 13.538 s | Misattributes a rejected erroneous equation to the learner; overstates fairness; introduces faulty percentage notation. |
| Local Llama 3.1 8B | 4.988 s | Contradictory arithmetic feedback; rejects an equivalent percentage; treats missing bin definitions as a learner error. |
| Configured OpenAI Luna | 2.461 s | Correctly handles rejected claims, equivalent percentage, missing boundaries and unequal retention in this sample. Socratic follow-up repeats an already answered calculation. |

The hosted comparison used only these synthetic inputs, no course content or personal answers, no fallback and no routing changes. Seven calls totaled **$0.002281 estimated** in the app accounting, below the requested $0.02 incremental cap. This is an estimate, not an invoice. Its explicit `--allow-paid` command uses the existing live accounting ledger and daily cap. Existing reservation locking is process-local: do not run paid CLI evaluations concurrently; the limit is not a cross-process hard guarantee. The completed run stayed within one UTC budget day.

Pricing ceilings were checked against the [official model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna); the registry's conservative input/output ceilings were required by the diagnostic. Local defaults remain entirely local with a disposable database and zero hosted budget. Hosted accounting records are the only live database writes from this comparison.

These are ordered single trials, not a latency benchmark, reliability estimate or learning-outcome study. Raw inputs, message hashes, outputs, attempts and timings are retained in `evals/results/answer-memory/quoted-feedback-*-initial.json`. No real learner answers are in these artifacts.

## Decision and next gate

Do not enable this experimental schema in live tutoring yet. Exact substring validation prevents invented quotations but does not validate whether a quotation endorses a claim, whether its judgment is true, or whether prose contains extra questions. A single hosted sample is promising evidence for this narrow task, not permission to switch every task to hosted inference.

Next: expand the synthetic cases to revised answers/history, missing execution output, conflicting evidence and long answers; improve Socratic follow-ups to extend reasoning instead of repeating an explained calculation. A runtime slice must preserve local deterministic checks and saved-answer reuse, bind feedback to the exact submission, retain drafts on failure, and keep provider/cost choices visible. General chat, hint requests and grading must not silently inherit this diagnostic route.

## Verification and review

Five contract tests cover quote substitution, request isolation, schema privacy, explicit-mode fields, Unicode/whitespace, oversized/empty answers and duplicate quotes. Review corrected an empty-string follow-up loophole by requiring `null` in explicit mode. No API, UI, dependency or database schema changed, so new UI journeys or generated API types are not required for this diagnostic. The preceding runtime commits passed both remote CI workflows, including all browser journeys.

Final verification: **547 backend tests passed**, with three existing warnings; full lint/format/mypy/TypeScript/ESLint passed. Independent code and pedagogy review found no remaining blockers or majors. The reviewer confirmed the narrow hosted findings and the redundant Socratic follow-up; broader reliability remains unproven.


## Expanded comparison — completed

Version 2 explicitly distinguishes revised claims from history, missing execution evidence, stale output and conflicting bin instructions, and prevents asking again for a calculation already supplied. The same original seven cases remain, plus six synthetic edge cases: revised answer with a wrong historical tutor endorsement, absent execution output, stale output after editing code, conflicting interval boundaries, a long answer with its conclusion at the end, and unequal denominators in Socratic mode. Both scripts now share these context overrides; earlier v1 artifacts stay immutable. No live tutoring route changed.

Acceptance: inspect semantic correctness separately for each case; exact quote validity alone cannot pass. Explicit mode stays question-free; a Socratic extension must go beyond the supplied/corrected calculation. Missing and stale evidence must remain unverified. Only synthetic input is sent in the explicitly paid comparison; the same accounting cap and limitations apply.

Expanded results: hosted 13/13 literal contracts valid, median complete response **1.945 s**, total **$0.004363 estimated** across these 13 calls. Manual inspection found correct handling of the supplied judgments and denominator-based Socratic extensions. This remains one sample per synthetic case, not a general accuracy guarantee.

Local Gemma: 12/13 literal contracts valid, median case duration **15.356 s** across all 13 cases including the failed case. It still rejected a correct revised answer and a correct 15-percentage-point difference, invented a fraction-format requirement, and hid extra questions in prose. The long-answer case recorded one error attempt and GatewayError after about 29.9 seconds; the artifact does not establish the underlying cause. Do not reinterpret this as a semantic pass. The contract can reject malformed quotes but cannot repair these wrong judgments. Raw attempts remain in the expanded artifacts.

Next runtime direction is specified in `docs/slices/explicit-answer-feedback.md`: a narrowly scoped explicit answer-check action, with provider disclosure, exact answer binding, deterministic arithmetic, retained work on errors, shared read-aloud and unchanged broader conversation routing. This diagnostic does not implement that action.

Verification: full lint/types passed; both CLI files pass Python compilation and targeted Ruff (E402 excluded for their explicit repository path bootstrap). All 13 request fixtures validate within existing bounds. Five exact-quotation contract tests passed. No backend runtime implementation changed since the 547-test pass. Earlier diagnostic commits now have separate CI runs; do not conflate those with this uncommitted delta.

Independent code/pedagogy review cleared the expanded diagnostic and planned runtime slice; it corrected an unsupported explanation of the long-answer failure. No remaining blockers or majors in this diagnostic.
