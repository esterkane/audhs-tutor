# Research prompt locality and language accuracy

## Scope — 2026-10-25

Incoming release 7793f55 CI completed with every gate successful except one browser journey:
495 passed, 20 opt-in skipped, one stale-preferences recovery failure. Its navigation fixture
could return before Home had actually replaced Preferences, so the expected mount-triggered
refresh was not guaranteed to happen. It now waits for the Home URL and removal of the old
heading before returning. Error/cached-data assertions and real preference-write assertions
remain intact; no retries, sleeps, timeout increases or product error handling were weakened.
Ten repeated runs across both widths passed.

## Stable evidence before changing findings

Research context now serializes source_passages before the current question/findings and
requests. Every existing field, source character, selected personal note and recent discussion
entry remains available; full saved histories remain unchanged. The same local model, output
limits, inference context limits, validation, hosted authoring controls and budget apply.
There is no model downgrade, speculative answer, automatic acceptance or additional inference
stage. Native inference can reuse more of the unchanged source prefix on follow-up requests.
Tracing records context_layout=source-prefix.v1. Existing versioned prompts are retained.

A bounded native-model comparison used synthetic Python notes, paired follow-up findings and
English/German requests, with opposite variant order. Warm-ups were excluded from follow-up
comparisons. Baseline prompt processing was 424/431 ms, versus 51/57 ms with the reordered
packet. Those are specific native timing observations, not a general response-time guarantee.
One German reply incorrectly described references as mutable; the uncorrected version was
not accepted on speed evidence alone.

Python policy v12 adds the precise immutable-value/identity and tuple-slot/list-content
distinctions supported by the [Python language reference](https://docs.python.org/3.12/reference/datamodel.html#objects-values-and-types).
A four-call correction trial covered both requested distinctions accurately. Prompt processing
remained 52/56 ms; follow-up wall times were 10.433/8.332 s versus baseline 8.844/10.171 s.
Generation varies and dominates the wait: these small samples do not establish faster decoding
or universal factual accuracy. No broader benchmark improvement is claimed.

## Research response language

Real browser drafting exposed a further gap: a German-profile draft still copied English
prose from English evidence. An extra system reminder did not fix it and was not retained.
The final research-specific, versioned reminder follows the closed untrusted context block,
using the explicitly selected German preference. It preserves the exception for a direct
request for another language and preserves quotations/code. The reminder participates in
the signed reuse binding; changed instructions cannot reuse the earlier mismatched reply.
It does not translate or rewrite old writing/history. The ordinary presentation policy remains.

The final real local-model browser flow produced factually correct English and German drafts
from English source notes, then used the proposed section, saved, reloaded and opened Review.
Both language/source meanings were reviewed; a browser journey's structural pass alone was
not treated as a language-quality pass. All unsuccessful trial outputs remain in private
evaluation records, not in the public repository. No hosted calls were needed for these trials.

## Verification and limits

Affected backend research/authoring, memory/source preservation, exact reuse, hybrid-budget and
native-schema tests pass; Ruff, format and strict mypy pass. The full 26 affected sandbox
browser journeys pass, including the incoming CI case, authoring/research, accepted reading,
assessment/feedback/recap, save/resume, notebooks, offline Python and optional quiet designs.
The two final real-model browser flows run in an isolated learner database, with hosted
authoring disabled there only, then restore its preferences. Main progress and scoped OpenAI
authoring settings remain untouched. Existing green backend/frontend/migration/bridge CI gates
are reused for unchanged components; new release CI is a separate pending snapshot check.

Broader unsupported claims, repetition, first-load latency and decoding speed remain open.
This is not a language detector or a universal hallucination guard. No cross-browser/human
assistive-technology, original-course training or general model-quality acceptance is claimed.
