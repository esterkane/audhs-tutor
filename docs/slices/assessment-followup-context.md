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
