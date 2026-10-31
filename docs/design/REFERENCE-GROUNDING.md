# Local project reference grounding

The Supabase project tutor searches official documentation as reference evidence.
Indexing references does not create, activate or replace learner-authored lessons.
Documentation, embeddings, acquisition caches and learner histories remain local data,
outside the public application repository.

## Exact identities and complete content

An explicit SQLSTATE request adds a parameterized lookup in the official PostgreSQL
error-code appendix for the database server's major version. Exact existing code and
class rows precede semantic matches; unrelated code rows are excluded. General prose
remains available. Every excerpt retains its real chunk ID, source URL and retrieval
timestamp. The search still respects product filters, result limits and text deduplication.
There is one query embedding and no additional text-generation call.

HTML reference extraction retains all table rows. Tables beyond 200 rows must not lose
their later error codes or configuration values. Refreshing a documentation index keeps
temporarily failed URLs eligible and only retires absent references on that index's origin;
references from other origins remain active. An empty index never retires everything.

## Local tool contracts and prompt size

The native project decision schema uses the actual argument models for the tools offered
on that request. Unsupported tools, missing required arguments and invalid enum/range
values fail validation before dispatch. Validated arguments return to the imported protocol
as JSON dictionaries, without inserting unset defaults. This adapter executes no tools.

The project adapter opts into whitespace compaction of the generated JSON schema appended
by Instructor. All schema fields, constraints and descriptions remain identical. Original
policy, history, user content, native format, context window and output allowance remain
unchanged. An unrecognized SDK layout uses the established prompt unchanged. This reduces
input work; it does not establish a general factual-accuracy or decoding-speed improvement.

## Verification boundaries

Regression tests cover table tails, exact source excerpts, mixed SQLSTATE lists, source
filters, safe retirement, typed tool arguments and the actual Ollama HTTP request payload.
The optional retirement integration test runs the generated SQL in a disposable PostgreSQL
container. It does not connect to a learner database. Browser authoring tests use isolated
learner data and fake providers; they verify workflow and persistence, not real-model accuracy.

Older generated explanation caches refresh to the complete-answer delivery contract.
Their saved historical answers and original provenance remain accessible; manual legacy
representations without a model call keep their unknown-provenance status.

A larger corpus and valid tool arguments do not prove correct causal explanations. Real
model evaluation must still inspect answer coverage, role/grant distinctions, old/new row
semantics, transaction chronology, language and source support before a model or inference
configuration is promoted.
