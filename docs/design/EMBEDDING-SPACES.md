# Local embedding spaces

Qwen3 Embedding 0.6B is an optional local embedding model in the registry. Its configured
768-dimensional output fits the application's reference-vector schema. The model supports
custom dimensions and multilingual retrieval; its model card describes a 32K context ceiling.
These capabilities do not by themselves prove retrieval quality on a learner's material.
[Official model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B).

Public routing defaults remain unchanged. Selecting the model is an explicit owner action,
separate from downloading its weights. Chat models, answer allowances, accepted content and
session histories are independent of the embedding assignment.

## Input and output contract

`routing_profiles.yaml` owns the model's embedding format: dimensions, document prefix and
query prefix. `ModelSpec` carries that validated format to every supported adapter. Qwen
documents use their original text; queries receive the model's retrieval instruction. Legacy
models retain their established adapter inputs.

The Ollama transport requests the configured dimension and sets `truncate: false`. It rejects
missing, empty, nonfinite or incorrectly sized vectors. Oversized input fails explicitly rather
than silently dropping its ending. Current Ollama embedding API truncates by default unless
this option is disabled. [API documentation](https://docs.ollama.com/api/embed).

For configured models, each batch receives enough context for a conservative UTF-8 byte bound,
up to the registered model ceiling. This does not change chat context or output limits. An
optional embedding context floor can keep bulk batches on one allocation; it only increases
capacity and never clips the input. Interactive calls retain the normal minimum allocation.

## Separate vectors before activation

The corpus builder honors the owner's explicit embedding-task assignment. Configured embedding
spaces have model/format-specific Qdrant collection names, preserving the legacy collection.
Personal-note collections already use the full model specification. Saved-answer vector keys
include the embedding format and installed weight digest. Old answers and their historical
provenance are retained; incompatible vectors are not reused.

An embedding change requires a rebuild, even when both models output 768 values. Equal
dimensions do not make their coordinates interchangeable. Rebuild corpus, personal notes,
eligible saved-answer vectors and any separately hosted project references using the same
model and input format. Keep the previous collections and a database backup for rollback.

For a local project reference database, stage vectors separately, verify every source/input
identity, and build the new index before activation. Preserve chunk IDs, source text and
citations. Switch the vector column and recorded model identity together, then update the
owner assignment and refresh cached repositories. Never expose a mixed old/new vector space.
The standalone project's legacy importer defaults are not an automatic migration mechanism;
its model/input format must agree with the selected project index before refreshing it.

## Benchmarks and verification

Embedding registry benchmarks measure vector compatibility and a small English/German
retrieval smoke test instead of invoking chat generation. Every attempt is recorded. Model
settings display dimensions, latency and retrieval checks; these are not factual-answer grades.
Broader retrieval and real tutor answer evaluation remain separate requirements.

Tests cover strict native payloads, Unicode-safe context bounds, vector validation, legacy
compatibility, isolated collection identities, owner routing, model-specific query inputs,
saved-answer keys and successful/failed local embedding benchmarks. Browser learning tests
verify authoring and persistence; fake-provider runs do not establish real-model factual accuracy.
