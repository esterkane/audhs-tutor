# Local project response framing

The local model returns a typed decision: learner-facing Markdown in `text`, tool requests,
and separate turn metadata in `state`. The adapter translates that decision into the imported
tutor's Markdown plus reserved `json tutor_turn` footer protocol.

A model can repeat the footer inside its `text` despite the native JSON response format.
Appending another identical footer makes the parser treat the first one as visible Markdown.
After a repair, this can expose protocol JSON beneath an otherwise complete explanation.

The adapter now reuses an existing footer only when it ends the response, has the complete
metadata key set, validates against the same metadata type, and equals the typed `state`.
Key ordering does not create a second footer. String provenance fields, including source timestamps, must match exactly; they are not rewritten.
The original response bytes are reused; no explanation or source passage is deleted or
paraphrased. The parser still owns extraction and the normal guard still checks the answer.

Partial examples, malformed JSON, conflicting metadata, four-backtick examples, and blocks
followed by explanatory prose are preserved and receive the ordinary canonical footer.
Tool requests retain their existing framing. This is not an instruction to strip arbitrary
JSON/code blocks or trust model metadata as learner evidence.

Regression coverage includes the real adapter/stream/parser boundary, complete written
explanation preservation, unchanged input history, and conservative example handling.
A recorded native response reproducing the duplicate was also replayed privately: two
footers became one, the written prose was unchanged, and no new inference was needed.

This framing correction does not establish factual accuracy or a general generation-speed
improvement. Source ordering, native metadata constraints and GPU/cache experiments require
separate factual, coverage, language, resource and history gates before deployment.


## Reviewed answers and requested output boundaries

Existing reviewed SELECT/RLS distinctions and incident plans honor explicit English/German
requests for no SQL, queries, commands or code. They keep the explanation, qualifications,
citations and follow-up while omitting the fixed diagnostic query block and its introductory
note. This does not expand the reviewed-answer matcher or establish broader model accuracy.
Output restrictions are excluded only from the concurrency report's negation check, so
“deadlock detected; do not show SQL” stays a report and “not a deadlock” stays negated.
Original request bytes and all prior/appended session messages remain unchanged.
