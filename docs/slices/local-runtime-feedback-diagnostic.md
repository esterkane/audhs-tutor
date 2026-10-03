# Local runtime feedback diagnostic

Adds `scripts/eval_local_runtime.py`, a synthetic diagnostic invoking the actual `playground.respond` service, including current prompt construction, request-bound feedback validation, deterministic arithmetic disclosure, answer persistence and exact saved-answer reuse. It uses the existing disposable SQLite world with no retrieval repository. Installed local candidates are explicitly pinned; production routing is deliberately not evaluated.

Before model discovery it rejects a non-loopback Ollama host. Before gateway construction it clears both hosted keys, sets budget zero, verifies the candidate is ready/local/Ollama and rejects any provider map other than Ollama alone. The fixed benchmark router cannot fall through to hosted models. No runtime routes, schemas, API or UI are changed.

Initial cases are wrong retention arithmetic, identical saved reopening, revised correct arithmetic and unexecuted Python indexing. Reports contain supplied requests, actual initial gateway message packets and hashes, runtime prompt version, raw final model text, model-call attempt identities/outcomes/token counts/latencies/cost, final displayed reply, saved feedback metadata and errors. Gateway repair message packets are not captured; their attempts remain visible in accounting. Runtime literal-validation success is separate from `semantic_review: not_reviewed`. A saved reopening does not claim fresh validation. Failed cases retain error type and any persisted attempts; interruption leaves report status interrupted_or_failed. Run completion means all cases were attempted, not that they passed semantic review.

Run sequentially from the repository root, after ensuring Ollama and the selected model are ready:

```sh
backend/.venv/bin/python scripts/eval_local_runtime.py --model llama31-8b --out /tmp/local-runtime-llama.json
```

The output path is reserved exclusively before setup: existing files are rejected without changing their bytes. Runtime invocation starts false and is recorded only when the response service is called. The pinned model identifies feedback generation; ancillary local embedding lookup can use a different local model. Use a distinct output path to retain previous evidence. This first slice is four ordered synthetic cases, not a benchmark or teaching-quality gate. A first real local inference run is recorded below; it does not establish a quality gate. Broader realistic notebook cases, conflicting evidence, held-out multi-domain cases, mode/adaptation follow-ups and repeated semantic review remain outstanding before any route recommendation.

Verification: 21 focused tests passed across new diagnostic tests, explicit feedback and answer memory. Fake-based integration invokes the unmocked response service, observes database persistence, proves zero-call exact reuse and changed-answer regeneration, inspects only-pinned-model error attempts, and verifies hosted credential stripping/zero budget and remote-host/hosted-candidate rejection. Additional regressions preserve existing report bytes and prove setup failure cannot claim runtime invocation. Targeted Ruff (existing script bootstrap E402 excluded) and format checks pass. These tests establish diagnostic mechanics, not model accuracy. Independent review and paired publication are handled by the integration owner.


## First real local run — 2026-10-03

One ordered synthetic run using installed llama31-8b completed four cases, with three local Ollama calls and zero hosted calls/cost. Wrong arithmetic took 11,890ms, exact saved reuse 11ms with no calls, revised correct arithmetic 4,673ms, and unexecuted Python indexing 4,925ms. These are single observations, not benchmark distributions. All generated replies saved and passed runtime literal checks.

Independent semantic review: exact reuse preserved reply/answer identity and disclosed no fresh checks; changed work regenerated and accepted 60%; Python correctly explained indexing without claiming execution. Wrong arithmetic corrected 0.9 to 0.6 but left the percentage conversion to the learner: partial pass against the literal “correct to 60%” criterion, reasonable formative scaffolding. “Partially correct” could more clearly identify the correct setup. The report's semantic_review fields remain not_reviewed so raw evidence is unchanged; this narrative records the separate review.

No production routing changed. The wider quality gate remains open: realistic notebook tasks, held-out domains, repeated runs, conflicting evidence and learning outcomes are untested. Code and pedagogy reviews of diagnostic mechanics found no remaining blockers or majors after output-preservation and invocation-provenance fixes.
