# Project explanation providers

Supabase/PostgreSQL project study defaults to local generation. Open the project page's
**Tutor provider** control to choose OpenAI for fresh explanations after configuring the private
OpenAI authoring credential and shared daily hosted budget. This sends the project question,
retrieved reference evidence and session context to OpenAI. Adding a key alone does not enable it.

Authoring and project study share one hosted daily allowance. Failed calls with uncertain billing
retain conservative reservations; choosing a provider does not make a model call. Missing setup
rejects the change and preserves the previous choice. Switch back to local at any time; this does
not clear sessions. Reviewed-answer reuse, accepted reading and query embeddings remain local.

The gateway validates the selected registry model and conservative context/pricing bounds.
Long-context study and shorter authoring have separate request limits. Histories remain append-only;
this feature neither summarizes away stored turns nor rewrites earlier explanations. Hosted models
can still be wrong; source citations and precise qualifications remain necessary.

Neutral discussion answers directly without initiating an assessment. Explicit teaching may add a
useful application check after the complete explanation. Protocol metadata lives outside visible
answer text; invalid hosted structure goes through the normal logged schema repair path.

SQLSTATE comparisons retain matching original question terms if a model shortens its search.
Canonical comparison names are resolved from active, product-filtered official PostgreSQL catalogue
rows, with exact chunk identity and source URLs retained. No built-in error-code answer dictionary
is used. Database mechanism searches also reserve up to two version-matched PostgreSQL manual
hits from distinct pages, while keeping framework context within the requested result limit.
Explicit product filters remain binding. Engine semantics use engine references when framework
wording conflicts; citations alone do not establish that an assertion is correct. Ordinary searches without an explicit SQLSTATE retain their original query path.

Anthropic credentials and the separately approved Claude Code review bridge are distinct. Claude
API transport uses the same exact-request study boundary, but the project UI currently exposes only
qualified local/OpenAI choices. The bridge still requires a specific approval for every consultation.

See [ADR 0025](../adr/0025-scoped-hosted-project-study.md).


## Interrupted questions and local drafts

The project editor retains unsent text and an unanswered outgoing question on this device,
scoped to the API, learner and session. A failed request can be restored after reload without
reconstructing or changing the server transcript. Nothing is automatically sent again. Restore,
append to a newer draft, or discard the saved question explicitly. A newer draft cannot overwrite
an unresolved outgoing question. Once a later answer is saved, pending recovery state clears while
newer unsent notes remain. If browser storage fails, the editor reports that failure and keeps the
current text in memory; copy it or keep the page open. Device drafts are not cross-device backups.

Session creation hides the previous editor until the new session is ready, avoiding text entry into
an editor that is about to be replaced. Stored drafts and prior completed transcripts are preserved.


## Disconnect accounting

During an SSE disconnect, the short database transaction that records an attempted model call
and settles its reservation is protected from the response's repeated cancellation. Unknown hosted
usage remains counted at the reserved bound instead of disappearing when an open reservation
expires. This cleanup does not retry generation or change the learner's transcript. Normal stop
requests still propagate cancellation. This covers graceful application cancellation, not a guarantee
against abrupt process or machine failure.

The project stream must end with a complete turn or an explicit server error. A premature EOF
exits the waiting state with a recoverable error; partial text is never accepted as a completed
answer. The client makes no automatic retry, and retained question recovery remains available.

Fresh hosted project turns first return a typed documentation-search request, rather than allowing
an unsupported final explanation before retrieval. A completed search from an older turn does not
satisfy this stage; a plain learner message cannot impersonate a tool result. Full session history
stays intact. Empty search results do not establish facts: the normal evidence/uncertainty contract
still applies. This adds no hosted call when the model would already search before explaining, and
can avoid later unsupported-citation repair; it is not a universal latency guarantee.


A project decision without a tool request must contain non-whitespace explanation text.
Metadata alone is rejected inside structured-output validation for both local and hosted
models. The ordinary gateway records that invalid attempt and applies its existing bounded
repair policy; it retains the original messages and requested output allowance. An empty
text field remains valid while requesting a tool. This protects against blank completed
answers, not against every omitted distinction or unsupported factual claim.


OpenAI and Anthropic adapters make one SDK generation request per gateway attempt.
Instructor v2 uses `max_retries=0` for that boundary; `1` permits an additional
internal validation retry. Transport retries are also disabled. The gateway owns
repairs, checks the remaining budget before another request, and records usage
and outcome for each actual attempt. Original messages and output allowances are
preserved. This does not change provider selection or the normal daily cap.


## Paragraph citation scope

The project tutor's price/limit/version citation-presence heuristic accepts a
paragraph-ending marker only when its citation entry binds to a source actually
returned by a tool, without inflating the source's trust tier. Its scope ends at
paragraph, list item, heading, blockquote, fenced code and table boundaries.
Unknown markers and unlabelled community evidence retain their existing guards.
This avoids unnecessary correction requests for a cited multi-sentence paragraph;
it does not establish that the cited source entails the claim or that the answer
is factually correct. Full source checks and factual evaluations remain necessary.


## Source-extracted SQLSTATE identities

In an explicit neutral discussion, a direct request for one to four SQLSTATE
condition names can be answered by extracting the exact rows returned by the
existing local documentation tool. The answer identifies the indexed PostgreSQL
major version, cites the retrieved manual and retains source/tool messages in
append-only history. No code-to-name table is built into the application and no
chat generation, inferred cause, repair or assessment is added.

This path requires all requested rows to agree in one versioned official engine
appendix. Missing, conflicting, unversioned or mixed-version evidence falls through
to the existing tutor. Questions containing further requests, explicit version
constraints (including earlier learner messages and the session objective), causal
reasoning, active labs, incidents, teaching or Socratic modes
also retain the ordinary tutor path. It does not silently change the session mode.
The session chooser offers an explicit "Discuss or look up facts" option for neutral
mode in English and German. The existing explicit and Socratic lesson choices and
resumed sessions keep their modes. This is not a general generation speedup;
broader local causal accuracy remains unqualified.


## Explicit literal-value membership lab

An optional disclosure in explicit neutral discussion compares NOT IN with a
correlated NOT EXISTS for one integer/null value and up to 20 integer/null inner
values, bounded to +/-1,000,000. The learner explicitly submits the form; it does
not execute general chat questions or accept SQL. The existing lab runner executes
a fixed scalar CTE as authenticated, inside its rolled-back transaction, with
schema-qualified built-in functions. No project tables or model-generated commands
are used. Actual equality, inequality and matching-row results are checked before
a deterministic bilingual explanation is rendered. FALSE and UNKNOWN stay distinct;
empty sets and duplicate values retain their actual semantics.

The form preserves edited values per learner/session and uses the existing pending
question recovery path, leaving an unsent research draft intact. Inputs, execution
results, documentation results and the complete explanation are saved in ordinary
append-only session history. Documentation retrieval can fail without replacing
actual computation with a model guess. No mastery evidence, mode switch, hosted
call or chat generation is added. Broader SQL and causal questions retain the tutor.
