# Exact research-reply reuse at capacity

An unchanged, server-authenticated saved answer can be reused after the twelfth reply. The cap
still applies before appending an answer or invoking a model. No history is truncated, and reuse
returns the existing draft without incrementing its version. The authoring UI offers a dedicated
Reuse saved reply action when the latest reply appears eligible; the server remains authoritative.
Ordinary new-generation and fresh-alternative buttons remain disabled at capacity.

The HMAC still covers learner, draft/question, inputs, answer, presentation and the applicable
policy/model contract. Changed actions, explicit fresh model requests and invalid signatures
cannot bypass the cap. Unattested full history is rejected before preparing a route. Model-path
context size remains bounded. Checked answers need no model packet, so large but schema-valid
findings/evidence do not reject a deterministic calculation; all text remains saved and signed.
No model, spending cap, context length or persistence schema changes are involved.

The existing signing key is process-local. Restarting the API invalidates optimization eligibility;
previous replies remain readable and editable as before. This slice does not introduce durable
attestation or claim that imported calculation labels are trustworthy; that investigation remains
separate. Client-side eligibility is an affordance, never authorization to trust a reply.

Verification includes API regressions for model and checked discuss/draft reuse at 12 entries,
unchanged versions/history, changed-action and signature rejection, fresh-model rejection,
zero additional inference, and a checked answer with oversized model context. Component tests
check the explicit reuse action and disabled generation; responsive sandbox browser journeys
exercise the twelfth answer, reuse, reload, retained eleven earlier replies and rejected new draft.
Affected authoring, source-research, accepted reading, feedback, recap and session flows are rerun.
All fixtures are synthetic. Exact release evidence is retained in local handoff records.
