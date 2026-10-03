# Local notebook feedback diagnostic fixtures

Adds the opt-in `--suite notebook` to the existing local runtime diagnostic. Default `basic` retains its original four cases. The eight new synthetic cases concern: within-group missingness denominators; a corrected answer on the same target; bin interval boundaries; representation before/after cleaning versus overall accuracy; unrun pandas code; a success claim contradicted by supplied KeyError output; stale output after editing code; and identifier/unit/missing-value meanings in a data dictionary.

Each fixture contains an explicit task, exact learner answer, code/output where relevant, stable synthetic target and separate fixed manual review criteria. These are authored synthetic inputs, not downloaded course passages, real learner submissions or freshly executed notebook outputs. The diagnostic runs the tutor service, not pandas/notebook code. Corrected denominator feedback requests saved reuse deliberately, but changed learner work must force a fresh answer.

Report version 2 adds suite/version/count and a SHA-256 fingerprint of every serialized request and review criterion (excluding disposable session ID). Existing per-case request, actual gateway packets, attempts, final reply and saved metadata are retained. Fixed criteria describe expected semantics but are never sent as hidden solutions to the model. Literal quote validity remains separate from manual semantic review, which starts `not_reviewed`.

```sh
backend/.venv/bin/python scripts/eval_local_runtime.py --suite notebook --model llama31-8b --out /tmp/notebook-feedback-llama.json
```

Choose a new output path; existing output paths are rejected. Hosted keys remain cleared, budget zero, loopback required, local candidate pinned and production routing unchanged. The integration run below exercises real local inference; the fixture authoring checks themselves use fakes.

Verification: six diagnostic tests pass, including two new regressions. They check explicit suite selection, unchanged default cases, evidence-sensitive fixture fingerprints, unknown-suite rejection, absent/stale/contradictory output markers and same-target corrected-answer intent. A fake-model test uses actual `playground.respond`, checks serialized request/gateway/saved work parity and proves corrected work is not replayed. These checks establish evidence plumbing, not teaching correctness. Independent code/fixture review and sequential local evaluation with semantic inspection are complete for this one candidate/run, as detailed below. Cases are a bounded initial sample, not a broad notebook certification or latency benchmark.


## Integrated local run — 2026-10-03

The eight-case llama31-8b run completed locally. Literal schema validation passed all eight, but
independent semantic review found two passes, one partial and five failures. The successful cases
recognized unrun pandas code and a supplied KeyError. Failures included reversed percentage ordering,
incorrect interval boundaries, endorsement of an incorrect denominator/identifier interpretation and
misattribution of stale output. The partial answer correctly challenged overall accuracy as a fairness
argument but invented group-specific improvements and omitted the requested calculations.

The candidate is not recommended for reliable answer checking on this fixture set. Production routing
was not changed. This bounded synthetic run does not establish other models' accuracy or a broad
notebook quality gate. Next: evaluate a stronger locally available candidate and improve grounding,
with deterministic validation where task structure permits; do not replace general evaluation with
hardcoded answers to these fixtures. Integrated diagnostic/reuse/feedback tests:23 passed.


A second local run with installed gemma3-12b yielded3 passes,2 partials,1 semantic failure and2
runtime failures (three invalid-output attempts each). Six displayed replies passed literal validation.
Corrected rates, unrun pandas and contradictory output passed; wrong bin boundaries remained, and
cleaning-representation/stale-output feedback was not delivered. This modest single-run improvement
does not justify routing changes. All calls were local; the broad quality gate remains open.
