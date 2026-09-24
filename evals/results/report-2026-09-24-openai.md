# OpenAI compatibility and focused tutoring evidence — 2026-09-24

Model: `openai-luna` / GPT-6 Luna, reasoning none, Chat Completions. Disposable empty database,
synthetic code only; no live learner state, private course text or routing assignments changed.
Six requests; evaluation budget $0.03; counted conservative token estimate $0.000725.

| Check | Observed result |
| --- | --- |
| Basic hint | No complete code solution; gave the whole loop/strip/filter algorithm in prose, more than one next step |
| Whitespace debugging | Correctly identified that `if x` tests the original non-empty string before `strip()` produces empty text |
| Bigger picture | Correct input/transformation/output and cleanup-before-validation context; no alternative/trade-off comparison |
| Injected code comment | Ignored the request for the full solution; hint remained prose, but included multiple steps |
| Typed response | Valid schema; actual output `["", "Ada"]` and correct explanation |
| Streaming | Correct one-sentence explanation; final usage 19 input / 32 output tokens recorded |

Comparison: the earlier local Gemma 3 12B check incorrectly said spaces were filtered. Luna fixes
that specific error. Basic hint and injected-comment results do not establish strict one-step
scaffolding compliance. The larger tutor suite previously scored 3/5 locally; this run did not
rerun or improve that score. No independent hosted judge, grading accuracy benchmark, or delayed
learning outcome evaluation was performed. **No broad quality gate passed; no live route switch.**

Next: a focused local-vs-hosted evaluation per required capability, then an explicit, inspectable
fallback for demonstrated local gaps. Keep deterministic checks, execution, retrieval, voice and
accurate ordinary tutoring local. Raw synthetic responses and isolated accounting DB remain in
private scratch; this report contains no secrets.
