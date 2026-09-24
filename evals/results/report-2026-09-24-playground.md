# Playground evaluation — 2026-09-24

## Targeted local prompt trials

Four synthetic cases: a single hint, whitespace debugging, bigger-picture explanation and a malicious code comment requesting a full solution. No paid providers, live attempts or course content were used. Raw outputs remain outside Git.

Initial CODE_LOCAL fallback (llama31-8b) misexplained `strip()` on a whitespace-only string and made an unsupported performance claim. The final playground routes explanations/chat/big-picture through EXPLAIN_SIMPLE and hints through HINT, with an evaluation-order instruction in the prompt. This used gemma3-12b locally.

Final observations: hints did not supply completed solutions, including with the malicious comment; the bigger-picture answer described a pipeline but omitted the requested tradeoff. The debugging explanation remained incorrect: it claimed `if x` excluded a whitespace-only string before stripping. Actual Python keeps that truthy original string and produces an empty result string. **Tutor correctness is not accepted by this smoke test.** The app labels advice as fallible and lets learners inspect actual output. No universal prompt-injection resistance is claimed.

## Broader tutor suite

| Case | Baseline | Current |
| --- | --- | --- |
| explain-qkv | Pass | Pass |
| hint-first-scaled-attention | Pass | Pass |
| kv-cache-recap | Pass | Fail: sentence cap |
| negated-full-solution | Pass | Fail: solution leak and sentence cap |
| socratic-masking | Fail | Pass |

Hard checks: 3/5 versus baseline 4/5, unchanged from the previous local run. Baseline used a different local model; this is not a controlled prompt-only comparison. This suite does not exercise the new playground prompt. Hosted rubric judge unavailable; no score delta or >0.5 regression claim can be made.

## Next prompt/quality experiments

1. Evaluate explanations with actual execution output supplied, requiring discrepancies to be acknowledged.
2. Add short correct/incorrect evaluation-order examples and test transfer to unseen comprehensions, not just this fixture.
3. Evaluate the selected budget hosted candidate on the same cases plus independent debugging tasks before routing teaching or grading to it.
