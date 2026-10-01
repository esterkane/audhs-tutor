# Explicit answer feedback — next runtime slice

Status: planned; no runtime implementation in this slice yet.

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
