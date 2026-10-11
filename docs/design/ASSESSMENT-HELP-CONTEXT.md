# Assessment help context contract

Status: required before publishing the pending feedback-help controls.
Design target: complete design system p10, four secondary feedback choices.

## Reproduced implementation gap

QuestionHelp currently sends the question stem and feedback as ordinary turn text.
Saved assessment records already retain assessment_question and assessment_result
in metadata, plus learner_answer and learner_answer_display in the saved request.
These immutable records are the appropriate source; current editable assessments
must not replace the checked version.

A second constraint matters: TurnRequest.text is limited to4000 characters and the
normal ContextPacket request budget is400 approximate tokens. Concatenating options,
code, criteria and learner work into that string silently loses task context. The
historical-answer budget can drop complete records, so using ordinary retrieved
history does not guarantee that the selected assessment reaches the model either.

## Required implementation boundary

1. Add an optional saved assessment answer ID to the turn request. Keep omitted
   optional fields out of existing idempotency fingerprints so old retries work.
2. Resolve it server-side for the current learner, session and skill. Require an
   assessment surface and a complete recorded question/result snapshot. Return an
   actionable error for unavailable or legacy incomplete records; never substitute
   current question content or another learner's record.
3. Put the exact checked question, options, recorded content version when present,
   submitted/displayed answer, feedback and criterion evidence into a dedicated
   untrusted-data section. Keep action instructions separate. Include saved record
   identity in turn history/cache identity; never reuse a generic cached explanation
   for different submitted work.
4. Give this section an explicit bounded budget and reject oversized context before
   inference rather than silently truncate or drop options/learner work. Preserve
   feedback and other navigation when help cannot load. The bound needs tests at
   its boundary, not an assumed guarantee that all notebooks/questions fit.
5. The UI supplies the saved answer ID and action only. If assessment saving failed,
   keep the existing save-retry control and explain why contextual help is unavailable.
   Generic conceptual help remains a separate capability, not a claimed full solution.
6. Label generated solutions as tutor-generated explanations, not verified answers.
   Saved grading feedback is evidence about the attempt, not an authoritative answer
   key or independent source. Solutions remain explicit; audio remains opt-in.

## Acceptance before publication

- Option-dependent MCQ: every option and selected text reaches the prompt unchanged.
- Criterion-dependent explanation: exact recorded gaps and work reach the prompt.
- Edited live question: explanation still uses the checked snapshot.
- Missing/foreign/wrong-session/wrong-skill record: no model call, no data disclosure.
- Oversized context: explicit failure, no partial task presented as complete.
- Existing request replay and context-free turns retain compatibility.
- Selected-record changes cannot reuse another answer's response/cache entry.
- Four controls remain keyboard-operable; Stop/error/retry keep feedback and exits.
- Fake-provider contracts and a separately reported local-model sample; do not
  present transport tests as tutoring accuracy or learning improvement.
- Code/pedagogy review, responsive visual checks, tests/lint/build and both publication
  variants. No new hosted provider or learning-policy change is required.

## Foundation in progress

assessment_help.load_context now reads the immutable saved assessment, scoped by
learner/session/skill/surface, and returns the recorded question, submitted answer
and grading result. context_block escapes embedded markup and rejects sections over
16000 characters (including wrapper) instead of truncating. Three focused tests pass
for saved work/ownership, untrusted markup/size rejection and incomplete legacy MCQ
records; initial mypy/Ruff checks pass. The helper is not connected to runtime yet.
Next wire optional request identity, dedicated ContextPacket rendering/budget accounting,
cache separation and UI save-state handling. Keep this unpublished until integration
and the full acceptance cases above pass.

Server integration in progress: TurnRequest accepts an optional assessment_answer_id.
TutorTurn resolves it against the session's learner/selected skill before inference;
ContextPacket renders the intact checked-assessment data section and records its
budget usage. Teaching-contract identity includes the saved record ID to separate
answer reuse. Existing idempotency payloads omit the new field when absent. Known
AppError messages are now returned in the stream rather than replaced by a generic
failure.34 assessment-context/ownership/recovery/preparation tests pass; mypy on the
four integration files and Ruff pass. Long option strings survive the packet without
request-budget clipping. No UI wiring or full integration acceptance claimed yet.
Next: regenerate API types, pass saved answer identity from assessment help, handle
unsaved results visibly, and exercise fake-provider captured prompts and local-model
quality before final reviews/publication.

UI integration: assessment help now sends only the saved answer ID plus chosen action
instructions. Unsaved outcomes disable contextual choices and point to feedback-save
recovery; generated explanations/solutions are explicitly not verified answers.
17 QuestionHelp/Session component tests pass. Six backend context tests pass, including
captured fake-provider prompts after editing the live question: saved options, answer
and criterion results are present, live replacement wording absent. Missing saved
records cause no model calls. TypeScript passes. Code/pedagogy re-review requested;
local-model sampling, remaining full validation and publication are still open.


2026-10-11: Four post-feedback help actions now use owned immutable saved assessment
context, including options, submitted work and criteria. Dedicated escaped context
rejects oversized/incomplete records; contract identity separates saved assessments;
legacy retry payloads remain compatible. No grading changes.31 backend tests,17 UI
tests,2 keyboard/responsive browser journeys, types/lint/build and code/pedagogy reviews
pass. Narrow help screenshot inspected; existing build chunk warning remains. One
synthetic local gemma3:12b sample (11.1s total, no hosted call) correctly distinguished
the selected expression from the correct option; its recipe analogy was less direct
than ideal. This is limited sampling, not evidence of general teaching quality or
learning gains. Broader local-model evaluation, human/AT acceptance and remaining
Progress/Explore design alignment remain open. See ASSESSMENT-HELP-CONTEXT.md.
