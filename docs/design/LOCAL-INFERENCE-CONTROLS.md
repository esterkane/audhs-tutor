# Explicit local thinking controls

Per-registry `ollama_inference_options` accepts `reasoning_effort` as a JSON
boolean or one of `low`, `medium`, `high`. Values are opt-in; omission preserves
model behaviour. For models advertising boolean thinking, an example is:

```json
{"qwen3-14b": {"reasoning_effort": false, "temperature": 0.2}}
```

Use actual JSON booleans, not strings or numeric substitutes. Before sending
content, the local adapter checks installed model metadata and requires an exact
value/type match with its advertised thinking capabilities. Unsupported settings
are denied. No remote model, endpoint, context or output-limit override is enabled.
The same configured control reaches plain, legacy JSON, native-schema and streaming
requests. Context capacity and requested output capacity remain unchanged.

Successful buffered responses expose a diagnostic `reasoning_chars` count in
model-call metadata when available. The count does not store reasoning text.
Absence of the count means unknown, not zero. It does not measure factual accuracy.

## Qualification boundary

A real isolated Qwen3:14b native-schema probe confirmed wire `think: false`, zero
returned reasoning characters, valid structured output and correct extraction of
supplied documentation fields. This is transport capability evidence only. Its
small output limit was specific to that two-field probe and is not a tutor default.
No live model defaults were changed. Before promoting a setting, compare complete
bilingual answers against source-backed factual cases and executable PostgreSQL
fixtures, including multi-part coverage and distant-history dependencies. Measure
load, prefill and generation separately. A small extraction probe cannot establish
a general tutor speedup or teaching qualification.
