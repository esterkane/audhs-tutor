# Tutor follow-up quantity roles — 2026-10-15

## Observed problem

A four-turn synthetic local conversation used the actual workspace response service with one pinned installed llama31-8b model, a disposable database, no retrieval or hosted fallback. It asked for correction, repeated the mistake, requested a simpler explanation, then changed a quantity's role in a what-if question. Each next turn included the actual previous replies, within the six-message history bound.

The first response correctly computed 30/50=60%. The second repeated the formula rather than explaining why adding counts cannot calculate a proportion, with unsupported “You're close” praise. The simpler explanation preserved 60% but repeated the same operation and added an unsolicited invitation despite explicit mode. The detailed follow-up changed retained30 to retained50 without permission: if50 now means removed, retained30 plus removed50 gives total80 and37.5%, not50%.

A scratch-only candidate instructed the model to preserve quantity roles, change only explicitly replaced facts, state assumptions and recompute denominators. It still returned50% for the preserved-retained case. A contrast explicitly changed retained to40 and removed to60; the candidate incorrectly reused total50 and returned80% instead of40%. Independent pedagogy review confirmed these failures. **Do not deploy this candidate as a fix.** No production prompt, route, assessment or learning-state rule changed.

## Evidence and limits

Baseline four calls: 4009/4435/3701/5803ms. Candidate two calls:6201/1983ms. All six recorded one local Ollama attempt, zero hosted cost. These are single observations, not latency distributions or accuracy rates. Literal arithmetic validation does not establish correct selection of the quantities or denominator. An additional sourced synthetic arithmetic probe correctly corrected0.9/90% to0.6/60%; that does not resolve follow-up context failure.

Raw packets, outputs and scratch runners are retained only in the private evaluation archive. The two synthetic counterfactual requests and manual criteria are reusable in `evals/cases/followup-quantity-roles.json`. They contain captured baseline history, not the candidate instruction. Run the baseline diagnostic using:

```sh
backend/.venv/bin/python scripts/eval_local_runtime.py --suite followup --model llama31-8b --out /tmp/followup-roles-new-run.json
```

The runner validates requests, supplies a fresh disposable session, hashes the manifest and retains the existing local-only gateway checks. Semantic review remains separate from runtime completion. 20 diagnostic tests and targeted Ruff/format checks pass; source review found no blockers. The fixture test verifies role-changing questions, history, session override and explicit mode; it is not a model-correctness test.

## Separate re-entry acceptance

Two existing persona browser journeys passed at1280/390px against a disposable real backend. They cover keyboard label/Undo/Pause/Continue, same-browser draft retention after reload, unchanged server checkpoint and fresh-browser-context return. Narrow Home screenshot inspected; no horizontal overflow, named Continue and saved activity visible. Browser-local draft loss in a fresh context is not server persistence. No model response or human comprehension was tested by these journeys.

## Next bounded step

Compare an already-installed local candidate on these exact frozen requests before any route change. Extend the matrix with an ambiguous role change and a non-numerical domain. Review preserved/replaced facts and assumptions before arithmetic and tone. Do not introduce a hard-coded correction for these numbers, silently rewrite learner facts, or claim a general tutor-quality gate from this sample. Main session tutor end-to-end semantic acceptance remains separate from this workspace service diagnostic.

## Installed-local comparison — 2026-10-15

Six calls total, two identical frozen requests per model. Normalized request SHA-256: `ba4442d0da847d9d222e18fb9ff35b1cfa5810cce2432950e5c8ea3a9d960d24`. One local attempt per reply, zero hosted cost; no routing change.

| Model | Role-change follow-up | Explicit replacement | Observed wall times |
|---|---|---|---|
| llama31-8b | Coherent0% under keeping original total50, but no acknowledgment that retained30 was replaced |40% result, invalid total explanation using50+50 instead of40+60 |14.485s /2.270s |
| gemma3-12b | Says zero remaining is impossible, then accepts it; confuses original total and remainder |Correct40% with coherent total100 |18.832s /2.895s |
| gemma3-27b | Computes0% retained then calls it not retained; invented citation marker is disclosed by existing source guard |Correct40% |37.163s /7.530s |

Gemma responses include unwanted representation prefixes;27B appends quizzes in explicit mode. Independent pedagogy review found no routing winner. These single-run timings include loading/other runtime effects and are not comparable steady-state latency estimates.

Rubric clarification: the first question is ambiguous. A coherent stated interpretation or focused clarification is acceptable;37.5% is not the sole permissible answer. The fixture criteria now explicitly permit keeping original total50 if replacing retained30 with0 is acknowledged. Requests remained unchanged, and raw reports retain their original criteria. This refinement does not excuse contradictions or a silent factual substitution. No new run was needed because criteria are reviewer metadata, not model input.19 diagnostic tests pass.

Source inspection found competing instructions: base policy requires representation prefixes while workspace task forbids them unless requested. The observed failures are consistent with this, not proof of cause. Next bounded experiment is documented in `docs/design/WORKSPACE-PROMPT-CONTRACT.md`; do not deploy a broader model switch or claim the quantity-role issue resolved.
