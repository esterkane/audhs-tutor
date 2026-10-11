# Workspace semantic cases

These synthetic cases target the production Study Tutor `respond` path, separately from attention-session cases. They do not grade learners or certify model accuracy.

Run from the repository root with an installed local model:

```sh
backend/.venv/bin/python scripts/eval_workspace_case.py \
  --case evals/workspace/retention-consistency.json \
  --out /tmp/retention-sample.json
```

The runner requires loopback Ollama, uses temporary SQLite, disables hosted keys/budget, and excludes grading/execution intents. It records first nonblank callback time, total time, delivered answer, prompt version and case hash. No browser timing, percentile, or learning improvement is implied. It does not unload or install models; current model residency influences timing. Retrieval is absent in this synthetic case.

Review each answer against every manual criterion and the reference arithmetic. Correct keywords are insufficient: an answer can repeat the numbers while reversing which group loses representation. Record a separate review; `review_status: not_reviewed` is intentional. An error preserves partial output without claiming completion.
