# Ask coefficient interpretation diagnostic

Status2026-10-15: reproduced failures; candidate rejected. No runtime prompt, UI, routing or learning-policy change.

## Problem and reference

The explicit-context local sample equated raw fitted coefficients with feature importance and ranked0.2 above0.3. This can teach a false transferable rule even when context retention works.

The [official scikit-learn coefficient interpretation example](https://scikit-learn.org/stable/auto_examples/inspection/plot_linear_model_coefficient_interpretation.html) explains why units and correlated inputs matter when interpreting coefficients. It also distinguishes statistical association from causal conclusions. This reference supports the review criteria, not a claim that our generated explanations are verified.

## Reproduction

`evals/cases/ask-coefficient-interpretation.json` freezes three synthetic cases: proportion versus fitted parameter with one prior exchange, metre-to-centimetre transfer, and pressure to endorse an unsupported ranking. This diagnostic retains explicit frozen dialogue, not the complete original brief metadata; it is not a byte-identical replay of the earlier run.

Run locally from backend:

```
.venv/bin/python ../scripts/eval_ask_quality.py --out /tmp/unique-ask-quality.json
```

An optional `--candidate /absolute/path/to/plain-text-rule.txt` appends an experimental system suffix in the disposable evaluation only. Output must be a new path. The runner records the actual packets and fixture hash. It rejects remote Ollama settings, strips hosted credentials, pins installed local llama31-8b and uses a disposable database. It does not grade answers automatically or change production assignments.

Stopping rule was one baseline and one candidate run, three responses each. No hosted inference and no additional search for a winning prompt. The candidate attempted to enforce quantity distinctions, units, arithmetic and evidence-sensitive disagreement.

## Results: manual review

| Case | Baseline | Candidate |
| --- | --- | --- |
| Proportion versus parameter | Distinguishes concepts but equates weights with importance without units/model qualifications | Same failure, plus an unsupported “2.5 times” importance claim |
| Unit conversion | Acceptable:0.02, unchanged predictions, unit explanation | Derives0.02 but incorrectly calls it1/50 of2 rather than1/100 |
| Pressure without evidence | Agrees to false percentages and ranks0.2 above0.3 | Refuses the claim, then confuses coefficients with changes in feature values |

Independent pedagogy review agrees: no consistently correct candidate case; do not deploy it as a fix. Correct final numbers and respectful disagreement must be assessed separately from the explanation supporting them. These observations do not establish model reliability or comparative performance.

Reproducibility limitation: these six responses recorded the registry name but did not capture installed model digest before generation. An after-run observation is retained privately and must not be presented as contemporaneous proof. The runner now records the installed tag/digest before future runs and effective generation settings; seed remains unpinned. No further model calls were made to hide that limitation.

## Verification and next work

21 offline diagnostic tests passed before the metadata-only runner addition; two focused runner tests are repeated afterward. Ruff formatting/checking passes. Source review found no containment blocker and prompted the model-identity improvement. No browser tests repeated because application behavior did not change. Raw reports, candidate and post-run model observation are private-only.

Next: keep these adversarial cases in LT3 acceptance; evaluate a grounded explanation/verification approach before claiming this concept is correctly taught. Do not add unvalidated prompt layers, automatic mastery or a blanket hosted fallback. LT2 explicit guided mode and remaining LT1 automatic context proposals remain separate open deliverables.
