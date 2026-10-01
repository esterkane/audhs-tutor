# Local saved-answer prompt evaluation

Run `uv run --project backend python scripts/eval_answer_memory.py --out <result.json>`.
Uses a temporary database, synthetic cases, the existing explanation route, only loopback Ollama, blank hosted keys and zero hosted budget. It does not run notebooks or inspect private course materials. Actual responses and elapsed/model time are retained; no automatic grade is assigned.

## 2026-10-01 evidence

Three paired cases (six calls each) were run with prompt versions v2, v3 and v4 on the locally routed gemma3-12b. Raw synthetic outputs are in evals/results/answer-memory/. Cases compare supplied correct context, intentionally wrong arithmetic and an injected instruction, with and without historical text.

- The model corrected 30/50=0.9 to 0.6/60% in the wrong-prior memory trials. This is narrow evidence, not general correctness.
- The injected instruction did not produce the requested degree-completion/fairness assertion. Some responses still overstate bias or suggest imputation as automatically fairer; these need further work.
- V2 used the prior answer ID as a citation. V3's explicit prohibition did not reliably stop this.
- V4 withholds IDs from model-visible context while keeping exact provenance in stored metadata/UI. It no longer exposes those IDs, but the correct-prior response invented `[1]`. **Citation fidelity gate remains failed.** Do not treat the prompt revision as a complete citation fix.
- Baseline responses sometimes omit the supplied numeric comparison and ask whether to explain further. Direct-teaching/task-fidelity acceptance remains incomplete.
- Prompt context is larger with memory. Single trials, order/cache/warm-up and differing response lengths prevent a speed comparison. No retrieval or exact-reuse timing was measured; only the earlier deterministic tests establish avoided model calls on exact reuse.

## Next gate

Resolve unsupported citation presentation without damaging notebook indexing/code syntax; test the final response path, not just prompts. Expand examples to missing evidence, ambiguous tasks and varied correct/incorrect prior replies. Measure repeated warmed runs and actual retrieval/reuse separately, with semantic matching still pending. No general teaching-quality or speed improvement is certified here.

Independent review confirmed the initial shortcomings. Backend contract regression ensures provenance IDs are withheld from model input but preserved in saved metadata. No UI/schema migration or paid provider change.
