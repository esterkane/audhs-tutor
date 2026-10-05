# Assessment follow-up context — 2026-10-05

## Reproduced problem and bounded fix

Completed feedback already stores immutable learner_answer, learner_answer_display, assessment_question and assessment_result. The generic saved-answer follow-up forwarded only the raw answer. For multiple choice this is usually a zero-based option index. A synthetic local arithmetic sample described the learner's answer as0 even though the saved selected option was4.

Follow-ups now use the stored displayed answer for assessment history, capped at8000 characters with explicit truncation metadata. The parent raw submission remains unchanged. Missing MCQ display text produces a limitation and no guessed choice; current question options and browser drafts are never consulted. Other saved-answer surfaces are unchanged. This adds no API, migration, learning writes, model routing or prompt-template change; the supplied historical input is corrected within the existing untrusted-data boundary.

## Evidence

16 answer-history/assessment-history tests pass, including original ownership/idempotency paths plus raw-index and text submissions, absent labels, bounded text and unchanged parent/assessment count. Ruff and mypy199 files pass. Independent review closed an initial false encoding assumption: MCQ also accepts option text. A first encoding-label candidate was additionally rejected because the local arithmetic reply confused the label with mathematical reasoning.

The final local-only Llama3.1:8b sample uses actual playground message construction, temperature0.2 and300 output tokens (application limit900), two synthetic cases before/after. Arithmetic after: identifies4 and explains2+3=5. Data-split after: identifies train/test on the same examples and explains unseen-data evaluation. Both before samples named0 as the choice. See docs/slices/assessment-followup-choice-context.json. These four samples are not a broad quality score or speed benchmark; no live learner database or hosted provider was used.

No frontend change, so prior layout/keyboard/browser evidence remains applicable; this slice does not claim a new visual result. Existing follow-up remains guidance, not regrading or fresh source verification.

## Next bounded implementation

Connect an explicit discussion action beside checked feedback to its saved answer_id and existing AnswerFollowup/recovery flow, without reconstructing submitted work from currentAnswer. Handle absent history/save-only receipt first. Keep original grade and frozen question visible; no automatic request, no mastery update and no reuse of a retry identity for changed work. Stream follow-up responses before expanding this surface so this does not reintroduce the buffered-response delay.

Verify follow-up lineage/ownership, unchanged attempt and evidence counts, paused/session-changed requests, Stop/late tokens, refreshed feedback, unavailable history, and keyboard/narrow presentation. A later misconception-specific prompt must be evaluated against the original answer, criteria and stored feedback; the concept-help slice is not that implementation. Review help-after-reveal and repeated-incorrect-answer journeys remain open.

## Integration inspection — 2026-10-05

The session assessment panel renders immutable checked feedback, its save status, and separate concept help. It does not mount AnswerFollowup. AssessmentSaveStatus already receives result.answer_id plus save_error/save_receipt, so no new assessment API or reconstructed currentAnswer is needed. The existing saved-answer conversation streams and retains interrupted drafts.

A direct mount is insufficient: AnswerFollowup currently chooses the current session globally, while Session keeps inactive teaching/assessment panels mounted under hidden containers. Therefore the integration must bind to the assessment session and explicitly deactivate on leaving the assessment view. Hiding a panel alone must not leave an invisible request running. A mismatched current session must show a recovery path rather than attach the old question to a different session. Closing discussion should retain the draft and partial text through the existing recovery keys.

Proposed minimal implementation files: frontend/src/routes/Session.tsx, frontend/src/features/programs/AnswerFollowup.tsx, an assessment-discussion wrapper if needed to keep the route small, their component tests and a focused sandbox browser journey. Add an explicit collapsed discussion action outside the live status feedback card; keep the checked question and grade visible. Missing answer_id must expose the existing save/recovery status, never fabricate a parent. Receipt recovery may produce a saved answer separately; do not confuse receipt identity with answer identity. No inference on opening the disclosure. No learning-kernel, prompt, model-route or database-schema change is required.

Acceptance must cover opening without a POST, an explicit streamed question with the frozen parent and bound session, original grade/attempt count unchanged, phase exit and pause aborting visible waiting, late tokens ignored, restoration after refresh, unavailable history, and keyboard/narrow use. This section records source inspection, not completed UI implementation or browser evidence.

## Delivered discussion entry — 2026-10-05

Checked feedback now has an explicit collapsed Discuss this feedback action outside its live-status card, using result.answer_id and the original session identity. Opening sends no inference request. Conversation streams through the existing saved-answer endpoint; original feedback and grade remain visible. No prompt, routing, assessment, evidence or schema change. No action is fabricated when history has not been saved.

Review corrected the initial unmount strategy: opened conversations retain component state on close/phase exit so failed-save replies and their receipts survive. Inactive conversations abort waiting, reject late tokens/completions and refuse retries; audio/dictation controls unmount and run their existing cleanup. Session mismatch renders a recovery link rather than sending against a new session.

Verification:13 focused component tests, TypeScript/build and ESLint pass. Two sandbox browser journeys pass (desktop390px narrow counterpart): real deterministic grading/history, explicit open without inference, keyboard Enter, mocked streamed discussion bound to saved parent/session, unchanged assessment POST count, close/reopen draft, saved history and refresh. Narrow screenshot inspected: controls wrap, no horizontal overflow, original grade stays visible. Independent read-only review found no remaining blockers after the reply-retention and media fixes. Browser discussion generation is mocked; this is lifecycle/interface evidence, not a new local-model quality claim. Existing real-local assessment-context evidence above remains applicable.

Remaining: save-receipt recovery inside AssessmentSaveStatus does not yet propagate its recovered answer_id to this action; use Open saved feedback after recovery. Completed unsaved replies still need broader durable restoration when leaving the entire route or refreshing; this change preserves them across disclosure/phase changes only. Full remote CI for this new runtime remains pending. Broader repeated-error learning acceptance stays open.

## Save-recovery connection — 2026-10-05

AssessmentSaveStatus now forwards the existing recovery callback. The session updates only the displayed result's answer_id/save metadata, enabling discussion immediately after explicit Retry saving. The wrapper remains keyed by attempt_id; its existing abort/identity guard prevents a replaced attempt's late recovery from changing the current result. Grading/evidence remain unchanged.

17 component tests, TypeScript and ESLint pass. Both desktop and390px sandbox keyboard/history/discussion journeys pass; the narrow case now simulates an assessment history-save failure and recover-save response, then verifies discussion targets the original real saved answer. Screenshot inspected: same wrapping and visible grade. This simulated failure tests UI wiring, not backend recovery internals. Independent read-only review: no actionable findings. Full-route unsaved-reply persistence remains open.
