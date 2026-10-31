# ADR 0024 — Initialize lesson retrieval when it is needed

Status: accepted for the existing lesson-turn endpoints.

The HTTP dependency previously initialized the retrieval repository before session ownership,
request replay and teaching-action selection. An unavailable embedding model therefore blocked
an already-saved answer or a literal-only prediction question even though those paths do not
search. Repository setup could also load an unnecessary embedding model before text inference.

The lesson endpoints now supply a request-scoped asynchronous repository loader to TutorTurn.
The ordinary retrieval branch resolves it once, through the existing get_repo function, shared
initialization lock, learner scope and source policy. Direct callers can still supply an existing
repository. Source-dependent explanations retain their search, widening, provenance and trust
checks. If a required repository is unavailable, the turn reports readiness failure rather than
continuing without retrieval. Streaming preserves the no_model_ready error code.

Completed idempotent replays return their original saved result before repository initialization.
Literal-only questions and conversation paths use the existing eligibility rules. Their traces,
events, answer snapshots and checkpoints remain intact; a no-model question keeps null model
identity. No database schema, assignment, hosted routing, budget, context or output limit changes.

## Socratic rendering correction

App-owned question stems now respect an explicit German preference. The existing literal-question
parser supplies German operation wording too, so German no longer needs a model merely to render
an already recognized expression question. Parsing and scope restrictions are unchanged: teaching
phase, Socratic follow-up, explicit recognized request, no assessed help, no spoken/conversation
mode. Syntax is copied, never executed or evaluated. The literal provenance version is v2.

The model-backed neutral-probe contract is also versioned for the renderer, while its data fields
and prompts remain unchanged. Existing saved answers are not rewritten. Model-generated situation
wording can still ignore the language preference; this decision guarantees localized app-owned
stems and the entire deterministic literal prompt, not general model translation or factual quality.
German natural-language request forms beyond the existing parser still use the model path.

## Verification boundary

Regression tests reproduce eager initialization before the fix, then cover both buffered and SSE
routes with all local models unavailable, saved model-answer replay with retrieval unavailable,
source-dependent readiness failure, identical saved replies and unchanged checkpoints. English and
German controller tests retain null inference provenance and perform no retrieval for literal probes.

A matched isolated real-tutor example took 22.155 seconds through the former German model path and
0.035 seconds through the retained deterministic path. This is one example, not a general decoding
speed claim. The exact expression, saved answer and latest checkpoint were checked. Broader model
accuracy remains open; experimental prompt/schema rewrites were rejected and are absent here.

The bilingual browser journey checks real HTTP transport, selected-language output, saved-answer
access after reload and narrow/desktop layouts. The focused complete workflow separately covers
upload, research, writing, review, activation, reading, notes, feedback and resume on isolated data.

Final local validation: 150 affected backend checks pass, strict mypy passes 330 source files,
and backend Ruff passes. Two selected-language browser journeys pass, as does the complete
isolated authoring-to-resume workflow. Frontend types and the new journey's ESLint check pass.
The previous full backend suite passed on the parent release; the new release still needs its
own GitHub CI result. These checks do not qualify broader model-generated answers.
