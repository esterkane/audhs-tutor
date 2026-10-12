# G0a — Model-provider transport containment

Owner policy: unknown/third-party/derived inputs stay local. This bounded slice
blocks external text inference before sending content or reserving budget; direct
provider calls, local embeddings and benchmark statistics use the same boundary.
It emits no learning events and changes no curriculum, grading, FSRS or mode rules.
There is no new screen or accessibility interaction in this slice.

## Problem and implementation

Code inspection found that API-key presence and registry provider labels permitted
external calls without version-bound origin evidence. Ollama's existing preload
checked local weights, but its actual inference paths did not. No historical
content is retrospectively approved. Positive owner-only hosted eligibility remains
unimplemented, so OpenAI/Claude currently deny all inference with a source-policy
reason and a local-model recovery suggestion.

The gateway validates the concrete adapter before each reservation, fallback and
structured repair. Missing validation capability fails closed; the deterministic
FakeProvider explicitly never transmits. Denied candidates may fall through to an
existing permitted local route, keeping the whole request. No hidden local route is
invented and no denied inference is recorded as an actual billable call.

Direct adapters repeat their checks. Ollama requires a loopback endpoint and a
successful, content-free /api/show response with local model metadata and no cloud
alias fields. Native and LiteLLM/Instructor payload clients disable environment
proxies and redirects. Clients are closed on completion/interruption. This assumes
a trusted local Ollama daemon; a malicious local service is outside this boundary.

## Verification

- Dedicated policy tests cover direct hosted complete/stream denial, caller metadata
  not granting permission, unknown adapters, zero reservation/model calls, complete
  context retained through local fallback, rechecking before repair, remote endpoint
  rejection, cloud/unknown models, embedding/statistics, proxy isolation and cleanup.
- Adapter protocol tests explicitly mock transport validation in their own files;
  production has no fake-key or model-name authorization exception. Policy tests
  exercise default enforcement separately.
- Final full backend suite: 1,345 passed (3 existing warnings). The subsequent
  repair-recheck case plus policy suite: 33 passed. Targeted adapter/policy suite:
  53 passed before that additional test. Ruff/format and strict mypy on six changed
  production modules pass.
- Real local smoke: installed small model returned a completion (945 ms) and stream
  through the pinned SDK client. Synthetic prompt only; this tests transport, not
  tutor quality or representative latency. No hosted requests or paid inference.
- Required review found a proxy bypass in the first patch. All payload clients now
  use pinned no-proxy/no-redirect transports; regression added. Follow-up review
  found no blocker/major. No learner context is stripped to make a request eligible.

## Remaining scope — G0 is not complete

The independent synchronous image reader and Kokoro speech output still need a
matching endpoint/transport boundary. This slice does not claim whole-app source
containment. Version-bound owner receipts, full derived ancestry/revocation,
public-export enforcement and historical content review remain outstanding.
Private backups are separate. Both repositories stay private.

Next: contain those image/speech paths, then implement the session-independent Ask
workspace described in ../design/CROSS-TOPIC-CONTENT-WORKSPACE.md. No new Ask UI,
automatic references/fact checking, generated video or course replacement is delivered
by this backend slice. Browser/keyboard/responsive checks are unchanged, not rerun:
no frontend files changed; human learning-quality and accessibility gates stay open.

Follow-up 2026-10-12: image/speech adapter containment delivered in
media-source-containment.md. Version-bound origin/lineage and public-export policy
remain incomplete; the limitations above are the historical G0a checkpoint.
