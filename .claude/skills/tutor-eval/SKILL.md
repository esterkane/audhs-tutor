---
name: tutor-eval
description: Run the tutoring-quality eval suite (rubric LLM-judge + hard checks) against current prompts and report deltas. Use after any prompt, routing or grader change, or when asked "run the evals".
argument-hint: "[case-glob | all]"
context: fork
agent: tutor-evaluator
background: false
allowed-tools: Bash(uv run python scripts/run_evals.py *) Bash(uv run pytest evals *)
---
# Tutor eval run: $ARGUMENTS

1. Run from the repo root: `uv run --project backend python scripts/run_evals.py --cases "evals/cases/${ARGUMENTS:-*}.yaml" --out evals/results/latest.json` (same as `make evals`; there is no root `pyproject.toml`). Needs Ollama for the local turns; the rubric judge runs only when `hosted-medium` is ready — say so in the report when it is not.
2. Hard checks (fail = 0 score): solution leaked before hint; missing citation when retrieval had hits; > 6 sentences per turn in default mode; feeling-question; learning-styles language; mode switch without flag.
3. Rubric (judge = `hosted-medium`): LearnLM five principles, 1–5 each, with quotes as evidence.
4. Compare with `evals/results/baseline.json`; report per-case deltas and any regressions > 0.5.
5. Write `evals/results/report-<date>.md`. Do not modify prompts in this run — report only.

Return: summary table + regressions + 3 concrete prompt-edit suggestions.
