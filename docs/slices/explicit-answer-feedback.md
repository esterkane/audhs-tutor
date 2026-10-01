# Explicit answer feedback — next runtime slice

Status: implemented; bounded acceptance passed. Broader teaching-quality gate remains open.

The learner chooses Check my answer on the current step, receives feedback tied to exact quotations from that submission, and can continue the conversation. The deterministic arithmetic notice remains separate from fallible model interpretation. No competency evidence, official grade or completion is produced. Existing stop, retained draft, target-switch and audio behavior must remain intact.

## Implementation contract

- Add a distinct `check_answer` intent requiring a nonblank bounded learner answer. General conversation, explanations, hints and answer follow-ups keep their existing route.
- Introduce a separately inspectable answer-feedback task using the evaluated provider for this demonstrated local gap. Show the provider and external processing before the explicit action, preserve budget enforcement and model preferences, and avoid silent fallback to models known to fail these cases. Key availability alone must not switch other tasks.
- Bind the validated response schema to the exact current answer and selected explicit/Socratic mode. Render readable feedback while preserving raw structured output, prompt version, supplied context and model accounting for saved answers. Quote validation proves attribution only; label the judgment as model feedback.
- Reuse eligible saved answers before generation; never replay a different intent, edited answer, changed context or obsolete prompt. Historical answers stay untrusted and cannot certify the present submission.
- Keep generated claims distinct from local arithmetic checks. Invalid output, unavailable provider or exhausted budget yields a retryable error with the learner's work retained. Do not persist a malformed reply as completed.
- The visible response and read-aloud must use the same final text. Escape quoted learner content so it cannot introduce active Markdown links or formatting. Do not infer code execution from a code snippet or stale output.

## Acceptance

Backend: missing/blank answer rejection; exact quote validation; explicit-mode follow-up rejection; failed attempts cannot save completed feedback; final text and structured provenance persisted; owner/session isolation; exact reuse excludes other intents and altered answers. Fake-provider tests prove contract behavior, not teaching accuracy.

Frontend: explicit provider disclosure; no background answer submission on hint/start; Stop and stale responses preserve work; validated feedback can be followed by chat; read-aloud parity; saved answer reopening. Isolated desktop/narrow and keyboard journeys plus production build.

Real model evidence: original and expanded diagnostics are prerequisites, not a universal quality guarantee. Keep unsupported source/execution claims and semantic judgments open to learner correction. Repeat the final runtime prompt on synthetic cases before release; no private course material needed for this verification.

Review: independent code and pedagogy review, relevant suites, handoff, consistent private snapshot and sanitized publication guard before paired commits/pushes. Both repositories remain private.


## Implemented — 2026-10-01

`check_answer` is an explicit intent requiring a nonblank answer. StudyTutor uses it only for Check/Review my answer, not explanation, hint, question-start or continuing chat. The separate `answer_feedback` task defaults to the evaluated OpenAI candidate. Its overrides select exactly one model; unavailable or failed local overrides cannot silently fall back to hosted. Budget accounting remains in the normal gateway. The UI discloses external processing and provides the model-settings link before the action. No other default routing changed.

Full selected material is included up to 8,000 characters; the UI refuses longer answer-check steps while retaining work, rather than omitting the question or criteria. Other actions retain their existing 1,000-character excerpt. Existing code/output bounds and source/execution limitations remain visible. No source retrieval is claimed.

The production feedback schema moved to `schemas/feedback.py`, with compatibility imports for old diagnostics. The renderer escapes learner quotations, labels judgments as fallible model feedback, and supplies the same readable final text to display, storage and audio. Raw structured feedback and exact submitted request are saved as provenance. Arithmetic notices remain independently generated. Prompt version v9 prevents replaying older free-text feedback; exact reuse still occurs before model generation. No database migration or competency evidence.

The final runtime message builder was evaluated with the same 13 synthetic cases using the actual check-answer intent and 650-token limit. All quote contracts were valid and inspected judgments appropriate in this sample; median completion 2.105 seconds, estimated total $0.004377. These are single trials, not a reliability or learning-outcome guarantee. The long-answer and missing/stale-output cases do not establish performance on arbitrary notebooks. Artifact: `evals/results/answer-memory/quoted-feedback-openai-runtime.json`. No personal material was sent in evaluation.

## Verification and review fixes

556 backend tests passed; final boundary change also receives focused route/schema coverage. 230 frontend tests, full lint/types and production build passed. Four isolated Chromium journeys passed (answer checking plus conversation at desktop/narrow sizes), including keyboard submission and visible audio controls. The final text/bound update receives a repeat of the two answer-check journeys. Screenshot inspected at 390px; no overflow or obscured action observed. Browser tests use synthetic replies, and component tests verify read-aloud text parity; no Bluetooth hardware claim.

Code/pedagogy review identified and fixed silent hosted fallback after a local override. Two integrated regressions use a ready hosted fake and verify it receives zero calls on local unavailability/failure. Existing feedback-report/CAS tests were preserved in their original file; new generation tests have a separate module. Review confirmed exact reuse, saved raw/readable output, rendering and final complete-material boundary. No remaining blockers/majors in this slice.

Remaining: validate broader real learning examples, improve follow-up continuity and reliability, and finish saved-answer recovery/correction gaps. A model judgment remains challengeable; quotation validity is not factual correctness. Personal voice, source coverage and other project queues remain open.
