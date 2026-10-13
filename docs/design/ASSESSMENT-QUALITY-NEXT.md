# Assessment quality after local grader diagnostics

Status: owner approved the recommended provisional-feedback policy on 2026-10-13. Implementation pending; runtime is not yet changed.

## Verified boundary
The current explanation grader accepts structurally valid model results at confidence >=0.6. That number is supplied by the model, not measured calibration. Initial accepted attempts can update competency and FSRS in `Grader._apply_result`; explicit task/rubric review controls separate Progress eligibility and does not verify a model's judgement. Existing model-origin disclosures remain useful but do not prevent incorrect decisions.

The experimental six-case criterion-ID sample produced a false pass at confidence0.7 and a directly contradictory pass at0.2. It did not exercise production acceptance or write learner evidence. This does not establish that those exact results occurred in live learning. It establishes that structure, quote presence and model-reported confidence are insufficient quality evidence for deploying the new contract. Runtime remains unchanged.

## Recommended temporary policy: feedback without assessed evidence
For future model-checked free-text explanations, preserve the submitted answer and model feedback as an explicitly provisional feedback record. Do not assign an assessed score, change competency/FSRS, or display a passed-check label from that provisional result. Keep deterministic checks, explicit learner self-report and existing historical records separate. No retroactive deletion or silent recomputation. This changes learning behavior and therefore requires owner approval under the existing Progress contract, rather than being a routine transport fix.

The learner must still be able to ask follow-ups, revise, inspect the rubric, challenge feedback, stop and continue learning. Display “Model feedback — not an assessed result”; no mastery claim. A reviewed task/rubric is still required for eligible assessed evidence, but is not sufficient by itself to approve model accuracy. Do not turn an error into a failed attempt, or automatically award a pass when the model is unavailable.

## Alternative
Keep current assessment behavior while treating the new transport as evaluation-only. Investigate a separate local verifier against the frozen question, complete rubric, answer and proposed judgement. A second model's agreement is not truth; it requires independent annotated cases and adds latency. No hosted fallback, model download, hidden extra inference or routing change follows merely from choosing this option.

## Implementation slices if the recommended policy is approved
1. Define provisional feedback storage/API and request-state outcome, distinct from assessed AttemptResult. Bind exact answer/content/review snapshots; idempotent retry and recovery cannot convert advisory feedback into evidence. Preserve owned backup/wipe and source restrictions.
2. Route only model-checked free-text outcomes to that record under a versioned policy. Test no competency, review or passed-label writes, including prepared/staged recovery and requests begun under older policy. Preserve deterministic checks and historical provenance. Decide outstanding in-flight request treatment explicitly in the storage contract.
3. Present feedback with continuing chat and revision, optional audio and clear saved state. Exercise keyboard, narrow layout, reload, double-submit, slow/error responses, Stop and changed content. Do not block learner continuation on a model verdict.
4. Revisit assessed model results only after an independently reviewed multi-concept evaluation measures false positives, false negatives, contradiction handling, evidence support and latency. Repeated runs and held-out paraphrases are required; six known cases are not a general quality benchmark. Never promote based only on model confidence or agreement.

## Acceptance and authority
No new policy is active yet. The owner approved implementation of the recommended policy on 2026-10-13; implement and verify the storage/API, routing and learner-flow slices before claiming enforcement. This document does not change the approved task/rubric wording, activated lesson, learning objectives, scoring rules or past evidence. The owner-approved Progress contract explicitly requires a separate decision for changing gating/scheduling. Further implementation must preserve local-first policy and bounded evaluation costs.
