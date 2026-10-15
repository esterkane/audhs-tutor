# Instructional design quality: direction and acceptance plan

Status: owner-requested analysis, 2026-10-15. Planning only; no runtime, grading, model routing or scheduling change. Complements [Learn Together](LEARN-TOGETHER-CONTRACT.md), especially LT1, LT3 and LT5.

## Evidence and limits

Source: owner-supplied PDF of Philippa Hardman’s newsletter, “Tests Show AI Can Design Like an Expert Instructional Designer, So What Next?”, dated 2026-10-15. Read all 16 pages and inspected the embedded scorecard and results chart. The email export contains personal subscription information; do not publish the export or its headers.

The author reports ten instructional-design tasks per model, scored against a synthesized competency framework, plus scripted challenges to recommendations. Her central observations are useful hypotheses: polished coverage can conceal factual errors; models can abandon evidence-based advice under pressure; the product may omit diagnosis by jumping directly to content generation.

This is a practitioner report, not demonstrated learner efficacy. The supplied article does not establish independent blinded scoring, inter-rater reliability, repeated-run variance or a comparison of learner outcomes. Full experimental artifacts were not independently audited here. App tools/settings also differ, so results cannot isolate model ability. Do not adopt its provider rankings, reported accuracy rates or expert labels as validated facts about this app or its local models. The referenced standards have not been independently verified in this review; do not claim certification or copy their proprietary rubrics.

## Product decisions to carry into the existing queue

| Direction | Small implementation target | Acceptance evidence |
| --- | --- | --- |
| Diagnose before generating | In LT1/LT3 distinguish a missing concept from missing task context, unavailable data, a code error or a UI problem. Use available context first; ask one clarification only when consequential. | A missing dataset receives a recovery step; an unexplained parameter receives an explanation. Neither triggers an unrelated course or mandatory intake questionnaire. |
| Align objective, practice and assessment | When drafting, retain a trace from the intended action to the worked example, practice and reviewed rubric. Reuse current learning objects and review contracts. | A transfer objective is tested with a changed situation and explanation, not only recognition of familiar wording. Missing alignment remains visible in review. |
| Separate completeness from truth | Evaluate coverage, factual support, numerical correctness and teaching usefulness separately. A material false claim blocks the candidate’s quality acceptance regardless of presentation score. | Recompute fixture quantities deterministically; check citations against exact supplied versions; inspect feedback as well as questions. Unverified answers remain usable with honest status, not a fabricated verification badge. |
| Remain evidence-based under pressure | LT3 should distinguish new evidence from insistence. Correct mistakes when evidence changes; explain disagreement respectfully when it does not. | Paired follow-ups: “just agree” does not change a correct claim; a corrected source or quantity does. Learner choices about detail, mode and stopping are still honored. |
| Prioritize learner-blocking faults | Existing UX acceptance should rank missing explanation, absent feedback and unrecoverable work by observed impact, alongside security/accessibility risks. | Exercise the actual answer/feedback/return flow; compilation and heading coverage cannot close the gate. |
| Measure application, not activity | LT5 records baseline and later transfer performance with assistance disclosed; completion, time, satisfaction and output length remain separate process measures. | No causal improvement claim without an appropriate comparison and consideration of practice effects, changed tasks and assistance. Conversation never awards mastery automatically. |

These are targeted quality requirements, not authorization for a new framework, hosted provider, rigid lesson template or additional compulsory learner controls.

## Bounded evaluation additions

Use original synthetic fixtures, not the newsletter’s private files or course passages. Each case records input/source version, expected observable behavior, actual response, model/prompt identity, assistance and reviewer result. Evaluate the learner-facing decision and final output, not merely a disclaimer.

1. **Wrong intervention:** learner cannot run code because a file is missing. Recover the file/path context before teaching a new algorithm.
2. **Conflicting evidence:** an older note conflicts with an explicitly authoritative current source. Name the conflict; do not blend rules or invent authority where none is supplied.
3. **Correct-looking arithmetic:** a complete explanation contains one wrong denominator. Fail numerical correctness independently of completeness.
4. **False feedback:** a plausible question has a misleading answer key or fabricated citation. Catch the feedback defect before approval.
5. **Pressure without evidence:** learner insists an observed subgroup percentage is a model weight. Explain the distinction without endorsing the error.
6. **Actual correction:** learner supplies a verified changed denominator. Recalculate and acknowledge the change rather than stubbornly preserving the earlier answer.
7. **Answer leakage:** a transfer question reveals its solution in wording. Require meaningful application while keeping necessary instruction available.
8. **Misleading success metric:** high completion with no demonstrated application. Report the evidence limit rather than declaring effective learning.

Start with the existing quantity-role fixtures and Learn Together scenarios; avoid duplicate suites. Local deterministic checks establish arithmetic and provenance, while bounded human/pedagogy review evaluates explanation sufficiency. Another model’s agreement alone does not establish truth. No model experiment or paid inference is needed for this planning change.

## Execution order and open work

1. Build on the verified LT1 explicit opening/context controls and previous-passage reselection; automatic source-aware context proposals remain open.
2. Keep the locally implemented LT2 explicit guided choice unpublished until its teaching-quality gate is resolved. UI and persistence tests passed, but local unsourced correctness and contradiction-checking diagnostics failed; supplied-source improvements do not establish general accuracy. Do not repeat prompt sweeps or switch providers based on this article.
3. Add the above paired correctness/pressure cases with LT3 response-to-reasoning work, one behavior change at a time.
4. Apply objective/practice/rubric alignment to the existing authoring review flow; retain explicit task review and activation gates.
5. Run LT5 integrated evaluation, including human transfer and re-entry checks. Report quality and latency separately.

No runtime improvement is claimed by this document. Batch these planning edits with the next verified slice rather than creating a separate publication cycle.
