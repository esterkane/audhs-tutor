# Grounded explanation revision and local comparison

2026-10-04. Bounded instruction improvement, not a model-quality gate pass.

## Change

Grounded prompt v2 asks for complete requested calculations, correction of relevant equivalent forms/units, honest irrelevant/absent/conflicting source treatment, precise operation attribution and separation of static reasoning from execution evidence. It preserves hint and learner-selected interaction limits. Grounded cache identity is now .lesson.v2, with a regression proving that old prompt answers are not reused for fresh requests. Completed request replay keeps its original response.

The repeated sample also exposed numeric-vector warnings with an empty linked retrieval result. An explicit grounded-marker mode now avoids that false warning even with zero passages; an unsupported standalone reference still warns. Historical source-free behavior is unchanged. This is syntax handling, not source entailment validation.

## Same seven-case local sample

Both candidates ran through the actual response path with the identical fixture hash, temporary DB and synthetic retrieval. All14 cases completed, using local-only pinned models; production routing and owner data were untouched. Independent review assessed model text against supplied passages, not just response validity.

| Case | Llama8B v2 | Gemma12B v2 |
|---|---|---|
| Supported | Partial: correct trace, missing citation | Partial: correct trace/citations, unwanted prefix |
| Conflicting | Pass: resolves by calculation | Pass: resolves by calculation |
| Irrelevant | Partial: correct result, no irrelevance disclosure | Fail: cites a fern passage for code behavior |
| Empty | Partial: no concrete result/absence acknowledgment | Partial: correct result, no absence acknowledgment, unsolicited quiz |
| Wrong answer | Partial: decimal corrected, percentage omitted | Pass: corrects0.6 and60% |
| Stale output | Partial: no static calculation | Partial: derives current result but labels historical output incorrect without its original context |
| Starter | Fail: already-completed computation described as unfinished | Partial: genuinely unfinished but example-data labeling and mode fidelity missing |

Llama v1 baseline:0pass/6partial/1fail. Llama v2:1pass/5partial/1fail. Gemma v2:2pass/4partial/1fail. These are single synthetic samples, not statistically reliable improvement estimates or production retrieval/learning-outcome evidence. Both remain below the desired quality gate. Gemma's invalid source attribution prevents recommending a routing switch merely from its higher pass count. Raw captures stay private and unmodified; application-marker regressions are separately tested.

## Verification and next step

50 affected backend tests pass, including prompt-version reuse rejection, linked sources, recovery, previous memory and marker behavior; Ruff and targeted mypy pass. Independent code and pedagogy reviews found no blocking implementation/instruction conflicts. No layout, keyboard or responsive behavior changed; no new UI browser run is claimed for this prompt-only slice. Actual local runtime requests are the affected flow evidence.

Next: introduce a distinct starter response contract with bounded Python code, explicit unfinished structure and checked dependency classification. A prompt asking for standard-library-only code is not enforcement. Re-evaluate starter relevance/unfinished work separately from structural checks. Source entailment, complete reasoning and interaction-mode adherence still require a broader repeated local comparison; no paid escalation or routing change is included. Broader C3 owner acceptance and C4/C5 remain open.
