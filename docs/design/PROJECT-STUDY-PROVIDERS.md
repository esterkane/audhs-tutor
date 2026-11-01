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
