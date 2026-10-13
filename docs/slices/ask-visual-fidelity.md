# Local Ask diagram fidelity trial

## Question and stopping rule

Can the installed default FORMAT route preserve the supplied explanation's causal
relationships and qualifications when producing the actual saved Ask visual schema?
Two synthetic cases (training-only parameter fitting, and a shared cause) use the
production worker/gateway, disposable SQLite, zero hosted budget and Ollama loopback.
No learner/course content, model pull or routing change. Three total attempts and
180 seconds maximum per case; baseline plus at most one revised prompt, then stop.

Separate gates: schema/storage success; semantic fidelity; latency; teaching quality.
No word-overlap metric or parse success substitutes for conceptual correctness.
Temperature0.1, max4096 output tokens, no fixed seed. Small sample, no general pass claim.

## Baseline: ask.visual.v1

Gemma3-12b completed both cases in one attempt each, with no fallback. End-to-end times
31.912s (initial model inventory unloaded) and15.516s (subsequent case). This is total
visual-generation latency, not first-token time or a repeated statistical benchmark.

Semantic inspection **fails** the preprocessing graph: its held-out-data node says
it must not be used in imputation, contradicting applying the saved training mean.
The edge HeldOutData → causes → DataLeakage drops the condition that fitting on held-out
values is the problematic action. Source references do not make either statement true.
The common-cause graph weakens rain causing umbrella use into mere association and
omits the input's qualification about other causes of wet pavement.

## Candidate: ask.visual.v2

Require action-specific nodes where nouns would erase conditions; complete-sentence
edge checks; distinction between fitting and applying; preservation of possibility,
causal direction and stated limitations. Human-readable displayed labels, no raw-ID
prose. Self-checking is explicitly not independent verification.

Candidate remains **inactive**. The sourced preprocessing case consumed all three
admitted attempts and timed out at180.010s; two invalid-output call records reported
unknown graph-source references. No version was saved. The unsourced common-cause
case completed in one attempt at26.562s and improved causal labeling, but still
omitted the alternative-causes qualification and repeated draft disclaimers in every
node. Final validity1/2, first-pass validity1/2, timeout1/2. Neither prompt earns a
semantic quality pass. No further trials were run in this bounded comparison.

## Reproducibility and limits

Installed gemma3:12b digest
f4031aab637d1ffa37b42570452ae0e4fad0314754d17ded67322e4b95836f8a;
llama3.1:8b fallback was installed but no successful call used it. Initial baseline
model inventory was unloaded; candidate inventory was warm. Cold/warm ordering and
one sample per case prevent a speed comparison. Invalid-output call latencies are
recorded as0 by the existing provider logging path, so use measured wall-clock time;
zero is not measured inference latency. Admission count is not proof of completed calls.
Runner/raw synthetic outputs are retained only in the private evaluation archive.
Candidate prompt is saved for review but not wired into the runtime.

## Recovery correction and next step

Prompt-version upgrades must retain the original owned request identity on replay.
The start route now resolves the prior prompt version by owner/key before reservation;
canonical binding and attempt-budget checks still reject changed payloads. A regression
covers old-version cancelled replay without inference and changed-input409.

Next: expose exact-version presentation feedback, and investigate source-reference
proposal ergonomics before another bounded quality evaluation. Preserve fit/apply,
conditions and causal qualifications as explicit review criteria. No automatic source
citation or schema-validity badge can certify generated teaching content.

Verification: six focused API tests pass; 1554 backend tests (3 existing warnings) and full lint/types pass.
Required code/pedagogy review cleared the retry fix and confirmed the baseline semantic
failure. Presentation-review controls and broader learner evaluation remain open.
