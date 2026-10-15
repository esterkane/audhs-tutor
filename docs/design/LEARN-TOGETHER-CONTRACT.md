# Ask and Learn Together — conversational teaching direction

Status: owner-supplied pedagogical direction received2026-10-15; implementation plan, not a completed feature. The reference dialogue is private. It is authoritative for the desired experience, not proof of its dataset claims, calculations or reported tool execution.

## Intended experience

The tutor helps the learner build and apply a mental model over multiple turns. It answers the learner's actual uncertainty, connects new information to their own reasoning, and explains why each distinction matters for the practical task. It should provide enough information to reason before requesting an answer. Neither a terse answer machine nor a mandatory quiz after every message satisfies this goal.

Preserve explicit explanation as the default. Offer learner-selected Learn Together for a guided conversation, with one purposeful question at a time and an immediate Explain instead option. A request for help or a confused response is not consent to a harder assessment. Conversational progress never becomes mastery or review-scheduling evidence automatically.

## Behaviors to implement and evaluate

1. **Respond to the learner's reasoning.** Identify the specific idea that is useful, uncertain or mistaken; explain the reason. Avoid generic praise and guessing what the learner understands.
2. **Explain before questioning.** Give the central distinction and a small example when needed. In guided mode, ask one question that applies that distinction. If the learner says they are lost, suspend the question sequence, restate the real task and available evidence, explain the missing prerequisite, and let them choose whether to continue.
3. **Keep the world clear.** Distinguish current project facts, observed local results, illustrative examples and assumptions. Label an invented example before introducing it, and again when returning to it after a context change. Never silently carry hypothetical numbers into the real project.
4. **Preserve the learning thread.** Keep the current practical goal, unresolved question, learner's proposed explanation and relevant factual anchors visible/recoverable. Connect each detour back to the task. Do not force irrelevant tangents just to introduce more terminology.
5. **Develop transferable distinctions.** Explain observation versus inference, descriptive statistic versus learned parameter, prediction versus cause, and group evidence versus an individual conclusion where relevant. Compare approaches and limits rather than giving a single unqualified rule.
6. **Use evidence honestly.** Claims of reading a notebook, computing a statistic or executing code require a real tool result tied to the exact local file/version/code. Otherwise say the claim is hypothetical, supplied but unverified, or not available. A familiar dataset name is not evidence of the currently loaded file's columns or row count.
7. **Make reasoning inspectable.** Give the relevant derivation, assumptions and evidence in ordinary language—not hidden model deliberation. Expand detail on request. Correct prior tutor errors explicitly and retain the correction history.
8. **Return to action.** Offer a meaningful next step in the existing notebook, local calculation or structured visual when that helps. Show what to change/run and what the result would demonstrate. Do not run generated code without the established execution controls or imply a figure proves understanding.

## Lessons from the reference's confusing moments

- The tutor introduced a different hypothetical dataset, then the learner could no longer tell what was real. Better examples alone do not solve this: persistent factual/source boundaries are necessary.
- The learner asked how inputs receive weights, but earlier turns had not explained how parameters are learned. When a prerequisite is missing, teach it directly instead of asking another inference question.
- A subgroup proportion is not feature importance, a coefficient is not a classification threshold, and mathematical correctness does not establish model validity. These are useful contrastive evaluation targets, not facts to hard-code into every conversation.
- Assertions that statistics were extracted from an uploaded notebook remain unverified here. Do not copy them into teaching content or mark them checked.
- Rich explanation is useful when requested; neither a fixed six-sentence cap nor a long multi-section response on every turn is appropriate. Use progressive detail without hiding the necessary context.

## Current implementation and gaps

- Ask has owned saved answers, parent-answer links, local generation/reuse, optional selected sources and follow-up history. Its generation context is currently bounded to three previous answer pairs (`MAX_HISTORY=3`); it has no explicit persisted guided-learning mode. A long visible conversation therefore does not prove the model has all earlier facts.
- Workspace tutoring already has explicit/Socratic request fields, selected task/code/output, bounded history, saved answers and explanation controls. These are reusable foundations, not proof of shared behavior across Ask, lessons and projects.
- The workspace policy-conflict correction is a separate bounded slice. It does not add guided mode to Ask, verify facts, or solve quantity-role errors.
- Existing local notebook, visual, source and audio components should be reused. No new UI library or hosted service is needed for this direction.

## Staged implementation

| Stage | Small coherent deliverable | Acceptance |
| --- | --- | --- |
| LT1: factual context and repair | Define a source-aware conversation brief and visible current task/evidence context; repair a confused turn without silently changing the objective | Long conversation, hypothetical detour, “I'm lost,” return to real task; never claim unavailable file/tool access |
| LT2: guided interaction choice | Add explicit Ask/Learn Together mode using existing tutor controls; propagate and persist it through follow-ups, replay and saved-answer identity | One meaningful question only when chosen; Explain instead works; stop/change topic retains draft/context; old replies disclose their original mode |
| LT3: response to reasoning | Use the learner's actual claim and missing prerequisite; support simple/detail/example without replacing the current question | Repeated wrong answers, valid alternative reasoning, ambiguous question, corrected prior model error; no automatic grading/mastery |
| LT4: grounded practice | Connect the current reasoning step to existing notebook, local calculation, visual and read-aloud affordances | Exact starter/task/data linkage, visible execution evidence and limitations, return to conversation; keyboard/narrow-screen and audio fallback |
| LT5: integrated quality acceptance | Evaluate realistic multi-turn journeys with local models and human review | Factual fidelity, explanation sufficiency, transfer, pacing, source honesty and learner control assessed separately; latency/cost reported without treating them as learning outcomes |

LT1 starts with a storage/context design against existing answer records. Do not silently make a model-generated summary authoritative. Preserve source/version IDs and distinguish learner statements, retrieved evidence and unverified tutor claims. Use bounded context to avoid replaying the entire conversation and unnecessary token usage; disclose omissions rather than inventing continuity. Learner correction, ownership, backup/wipe, retries and source transport restrictions must remain intact.

## Required evaluation scenarios

- The learner gives a plausible partial answer; tutor explains its limits before asking a new question.
- A hypothetical example is introduced; learner asks whether those facts exist in their file; tutor separates facts and examples without claiming inspection.
- The learner says “I'm lost”; tutor resets context and explains the missing concept without demanding another answer first.
- The learner changes one condition; other facts keep their roles or ambiguity is acknowledged.
- A descriptive proportion is mistaken for model importance; tutor explains the distinction and offers a testable next step.
- The original goal drops out of the short history; the tutor uses verified context anchors or honestly asks for the missing context.
- A prior response claimed a calculation without execution evidence; correction is explicit, saved and searchable.
- The learner wants a direct answer, stops, returns, changes topic or uses only keyboard/audio; mode and context remain understandable.

No learning-outcome claim can be closed by prompt-string checks or simulated learners alone. Keep the owner's task/rubric review and provisional model-feedback policies.

## Instructional-design quality supplement

The owner-supplied instructional-design report is assessed in [Instructional design quality](INSTRUCTIONAL-DESIGN-QUALITY.md). Carry diagnosis before content generation, objective/practice/assessment alignment, independent factual checks, evidence-sensitive disagreement and application-based evaluation into LT1/LT3/LT5. These are acceptance requirements, not evidence that this app or a particular model already meets them. Preserve learner choice and the existing provisional-feedback policy.
