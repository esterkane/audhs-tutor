# ADR 0023 — Explicit local inference controls

Status: accepted as an opt-in capability under the local accuracy and latency work.
This decision does not select or qualify a new default model.

Some local models advertise named reasoning levels. Ollama can silently use a default for an
unsupported name, and the current SDK maps named levels on unfamiliar model aliases to a
boolean. A configuration label alone therefore does not establish what was requested.

`OLLAMA_INFERENCE_OPTIONS` maps a registry ID to optional `reasoning_effort` and `temperature`.
The default is empty. Configured values deliberately override that model's per-call generation
defaults across plain text, legacy structured JSON, native schema, streaming and speed probes.
The same context and output limits remain in force. No endpoint, model, output or context
setting is accepted in this object. No transport, routing, hosted authorization, grading,
learner-state or saved-history policy changes.

Before sending learner content, the adapter verifies local weights and checks that the exact
named level is present in the local model's `/api/show` `thinking.values`. Missing or unsupported
metadata refuses the configured route. Default/unconfigured models retain their old behavior.
The SDK receives the native `think` field to preserve supported levels for custom aliases.

Every gateway attempt, including a validation repair or stream, records the explicit requested
options. The benchmark summary also records them. These are requested settings, not invoice
claims, semantic validation or proof of what an arbitrary server actually computed.

Example for an already registered, locally installed model whose metadata advertises the level:

```dotenv
OLLAMA_INFERENCE_OPTIONS={"my-registered-model":{"reasoning_effort":"medium","temperature":1.0}}
```

Configuration is device-owned and read at process startup. Changing it requires a restart;
process-local discussion-reuse integrity is then invalidated while saved replies remain.
A lower reasoning level or a faster benchmark is not a quality qualification. Any model
assignment still requires measured complete answers, source criticism, language consistency,
causal scope and the affected learning workflow. Do not use these options as an automatic
fallback or silently apply an untested mode to ordinary learning.

See [Ollama thinking controls](https://docs.ollama.com/capabilities/thinking).


## Verification boundary

Transport tests cover plain, structured JSON, native schema, streaming and speed probes,
including custom aliases, unsupported capabilities, remote weights and repair accounting.
The isolated focused browser flow covers uploaded sources, research, writing, review,
activation, reading, notes, feedback and resume; six additional desktop/mobile checks cover
reading and imported history preservation. These workflow tests use the existing fake sandbox
provider and establish integration behavior, not the factual quality of a candidate model.

Actual local research-service comparisons rejected lower reasoning for incorrect claims and
high reasoning for incomplete output within the existing budget. No candidate is assigned by
this change. Full histories, context ceilings, output limits and normal routing are preserved.

Validation: full backend 2,593 passed and one skipped; strict mypy passed 330 source files;
affected Ruff checks pass. Focused browser workflow passed, plus six desktop/mobile reading
and saved-history checks. All learner data was isolated. No default model was promoted.
