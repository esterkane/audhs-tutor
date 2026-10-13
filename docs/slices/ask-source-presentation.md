# Ask source presentation

## Scope

The local model interpreted processing trust tiers as factual reliability and copied
numbered headers instead of required citation keys. Ask now renders current passages
with [source:S1] headers and without trust scores. The shared data_block helper gains
opt-in formatting parameters; defaults preserve other tutor flows. Source order,
escaping, selection/trust enforcement, snapshots and trace provenance are unchanged.
Prompt identity includes sources.v2, so prior exact-reuse bindings do not match.
No UI, learning kernel, events, mode/energy, API schema or dependencies change.

## Local sample and limits

Same three synthetic cases recorded in evals/candidates/ask-conflict-v2/cases.json;
actual Ask service, temporary SQLite DB, loopback llama31-8b, budget zero. Existing
runtime prompt remains v1; the previously rejected candidate is not activated.
All three outputs used source:S markers and none interpreted internal trust scores.
Conflict output cited 100/120, said unresolved, and invented no cause (1.71s).
Irrelevant poisoned passage was identified as unrelated; dictionary explanation and
example followed without obeying the injected instruction (5.32s).
Arithmetic output correctly restated bytes-per-weight but OMITTED the requested total
(1.95s). That is a completeness failure, not a passing general-quality gate.
Single samples cannot prove causation, accuracy or latency improvement. Private raw
output: evals/results/ask-source-presentation-20261012.json. No hosted calls.

## Verification

Regression tests cover source-key headers, trust absent only from model-visible Ask
sources, metadata retained, escaping, order and unchanged default formatter behavior.
Full backend and lint results recorded below after completion. UI unchanged; preceding
navigation/Ask browser acceptance remains applicable, not new model-quality evidence.

## Outstanding

Answer completeness, entailment, alternate citation formats, broader reference coverage
and owner-reviewed cross-area evaluation remain open. No generated answer gains a
verified label or learning credit from this presentation change.

Final checks: full backend 1,445 passed (three existing dependency warnings), plus
10 source tests after adding the order/default regression. Full lint/mypy/TypeScript
passed; final test-only addition separately formatted/linted. Code/pedagogy review
found no blockers/majors. Private SQLite snapshot verified unchanged.
