# Prepare the local tutor after session start

2026-10-05. Bounded first slice; existing-session resume is not covered yet.

## Evidence and implementation
Ollama logs for the synthetic saved-answer sample show 6.03 s runner startup and 6.62 s prompt evaluation before a 13.05 s first-text observation. Earlier wording attributing most of that sample to prompt processing was incomplete. All 49 layers were on the GPU and flash attention was enabled; enabling these again would not help.

The documented empty Ollama chat request loads weights without generating text. This is scheduled after delivering a successful new-session response, resolving the current explanation route from the registry. Only an actual local Ollama provider, loopback host and installed non-remote model qualify. No downloads, hosted fallbacks, prompt edits, model switches or learning writes. Use the existing keep-alive setting; skip preparation when it is zero. `OLLAMA_PREPARE_ON_SESSION_START=false` disables this independently of residency (default true).

Changed: session API scheduling, a bounded preparation job, Ollama adapter, Settings, focused tests and setup documentation. Preparation gets its own model_preload diagnostic entry, not a tutor answer or assessment. Session delivery must not depend on readiness, duplicate jobs must coalesce, errors must not undo a started session, and background work must use its own database session.

## Verification gates
Test empty payload/no generation, loopback/remote-model restriction, hosted/unavailable skip, configured duration/disable, duplicate scheduling, failure isolation, no evidence writes and actual response-before-load ordering. Run affected backend and session browser journeys. Measure a real local empty request separately; it is not proof of a universal response-time improvement.

Sources: [Ollama preload contract](https://docs.ollama.com/faq#how-can-i-preload-a-model-into-ollama-to-get-faster-response-times), [upstream show metadata](https://github.com/ollama/ollama/blob/main/api/types.go).


## Verified result
- 39 focused backend tests and full backend 869 passed; Ruff and mypy 200 source files passed. Seven isolated Home/session browser journeys passed. UI markup/styles are unchanged; prior visual/keyboard/responsive evidence remains applicable, not newly certified by backend tests.
- Independent review found a pending-slot lifecycle bug when response delivery fails. Claiming now occurs inside the background coroutine before its first await. The actual failed-ASGI-send/subsequent-start and concurrent duplicate tests pass; reviewer recheck clear.
- Real warm empty-request smoke: 37 ms, no generated text.
- Controlled isolated Ollama 0.33.3 instance on a separate loopback port, existing weights only, no live learner database or hosted provider: cold request first text13.115s, total16.031s, load6.735s, prefill6.364s. After unloading only the isolated instance and preparing it, the empty preparation took3.012s; the next request first text6.060s, total8.977s, load0.003s, prefill6.049s. Both had1606 input and82 output tokens and identical output with fixed seed7/temperature0.2. No prefix was reused across the unload. The isolated server was terminated afterwards; the owner's server was not restarted or unloaded. Raw synthetic evidence:local-tutor-preparation-sample.json.

This moves weight-loading work earlier; it does not make computation disappear. Benefit depends on preparation finishing while the learner reads. It can retain roughly 8.3 GB for this model under the existing keep-alive policy. It neither warms prompts nor pre-generates answers. A new session selecting a hosted provider, unavailable model or remote Ollama endpoint skips this optional work.

## Remaining limits
Existing-session resume, a later model switch and expiry after a long reading interval are not covered. Prompt evaluation still takes roughly 6 s in this controlled example. Do not claim a universal sub-two-second response. The identical model outputs contained an existing reasoning issue: contrasting counting forward with addition as if they were different operations, and inferring why the learner erred. Preserving identical output is not a teaching-quality pass; no prompt or model was changed in this slice.

The preparation job can finish loading after the learner leaves; it makes no content/progress writes and residency expires normally. It is bounded to 30 s and logs its own model_preload operation (success/error) rather than an explanation or learning event. Separate remote browser UI failures remain tracked in saved-answer-streaming.md.

CI follow-up: run37321419639 completed with226 passed,20 skipped and5 failed browser cases. Two failures were stale retry fixtures still intercepting the buffered endpoint. Those fixtures now intercept SSE with the explicit default purpose while retaining original-key/body and edited-draft assertions; both desktop/narrow cases pass locally. The three previously documented Home/visualizer failures remain. Full latest-head remote CI remains open.
