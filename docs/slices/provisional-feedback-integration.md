# Provisional model-feedback integration

Model-checked free-text explanations now produce `provisional_feedback`, not assessed results. The approved policy prevents unreliable model judgements from changing mastery or review scheduling. Deterministic checks and historical assessed outcomes retain their existing behavior.

## Implementation
- Local/hosted free-text application, including staged recovery, commits advisory feedback, a searchable answer snapshot, an advisory event and the completed request receipt atomically. No assessed attempt, competency evidence or FSRS write is created.
- Requests without a client key and direct grader callers receive independent internal request claims. Direct caller instances remain reusable. Completed historical model receipts replay unchanged.
- Revisions use separately validated feedback roots. A first advisory revision of an old assessed answer records `previous_assessed_attempt_id`; it does not rewrite historical learning evidence. Drafts preserve answer, outcome kind and identity through reload.
- Saved feedback and contextual help bind to the exact owned question, answer and recorded outcome. Live question edits cannot substitute a new question in historical discussion. All model observations remain explicitly unverified.
- Session, challenge, listening, code explanation, recovery and saved history handle the outcome union. Optional audio stops when its panel closes. Continue and question rotation recognize exposure without awarding a pass.

## Verification
Backend tests cover real HTTP with synthetic providers, unchanged historical replay, local/hosted paths, repeated direct callers, no-client-key submissions, revisions, ownership/content rejection, concurrent workers, atomic rollback, staged/prepared recovery, retained task-review bindings and exclusion from qualified Progress evidence. Frontend checks cover recovery, revisions and all affected outcome consumers. Two isolated browser journeys cover desktop/narrow layouts, keyboard disclosures, saved answer visibility, revision drafts across refresh, and advisory submission. Screenshots inspected; no horizontal overflow.

Full lint/type checks and production build passed. Migration tested on a consistent database copy before application. Code and pedagogy review findings resolved: hidden audio cleanup, saved-history observations/wording, and request isolation for reused direct callers.

These are behavior/contract checks, not evidence of model accuracy or learning improvement. Browser submission responses are fixtures; persistence and contextual model help are tested separately through HTTP with fake providers. Physical audio and human accessibility acceptance remain outstanding. No paid model calls were made for this change.
