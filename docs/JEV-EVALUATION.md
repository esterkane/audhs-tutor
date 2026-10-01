# Jev suitability for AuDHS Tutor — 2026-09-24

Recommendation: evaluate as an optional narrow classifier; do not integrate into the live learning path yet. Current implementation remains local-first and no TypeSafe key, dependency, adapter or model route was added. No Jev benchmark was run.

Jev returns typed choices, yes/no probabilities and scores; it does not generate teaching prose. Current official Jev 1.13.0 pricing is $0.042 per million input tokens; output tokens are free. A hypothetical 10,000 requests of 2,000 billable input tokens each totals $0.84 before retries or other services. This is arithmetic, not measured cost. Official deployment documentation describes a hosted API; a supported downloadable local model was not established by this review.

Best potential fit: source-role classification, area relevance proposals, and detecting course-orientation questions. These address demonstrated local source-selection gaps. Poor fit: explanations, lesson or preset generation, exact code/JSON validation, DSP/math, or controlling learner mastery. Keep deterministic rules, the kernel and the learner in control. Confidence is not proof of correctness.

The official limitations cover literal interpretation, numerical precision, indirection, distracting context and adversarial inputs. English has strongest support; German material needs a separate evaluation. Typed output prevents malformed schemas, not incorrect classifications. The official model page says requests/responses are not used for training and mentions enterprise ZDR; do not infer universal zero retention.

Evaluation before implementation: use a reviewed synthetic or public set with substantive prose, code-only examples, asset reports, introductions, ambiguous topics, German/English cases and injected instructions. Compare existing rules, the installed local model and Jev on false inclusion of irrelevant material, missed useful evidence, abstention rate, latency and total cost. Include the Canva/canvas and character/CharacterTextSplitter cases. Tune thresholds on a separate calibration split, pin the model version, and keep a human-review route. Do not send purchased corpus or learner data for this assessment without explicit scope.

Only if it shows a useful measured gain: propose a narrow decision-provider interface behind existing budget/logging boundaries, default disabled, with timeouts and local fallback. Do not force decision-only outputs into the existing generative provider contract or silently change teaching/grading routes. Any new hosted task must follow the project's ADR conventions.

Primary sources checked:
- [Official model reference and pricing](https://docs.typesafe.ai/models)
- [System One concept](https://docs.typesafe.ai/concepts/system-one)
- [Known Jev 1.13 limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13)
- [Official quickstart](https://docs.typesafe.ai/introduction/quickstart)
