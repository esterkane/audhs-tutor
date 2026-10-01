---
name: audhs-visual-benchmark
description: Harden and run local diagram-spec model evaluations for the AuDHS V01/V02 queue, separating parse validity, semantic fidelity and latency.
---

Read docs/VISUAL-LEARNING-QUEUE.md, active schemas, routing and evaluation conventions. The uploaded benchmark is reference code, not an approved runner. Share production validators; malformed types must return failures, not crash. Enforce all envelope fields. Use the installed real Mermaid parser; structural lint cannot pass its validity gate.

Use an explicit installed-model list, loopback-only endpoint by default, bounded requests/response sizes, cancellation and saved partial results. Do not pull models or globally install a parser. Keep learner passages/raw outputs private; public fixtures and summaries must be synthetic and sanitized. No automatic model reassignment from a benchmark.

Record model digest/options, prompt/schema/parser versions, sample size, seeds where relevant, cold/warm status, first-pass and final validity, total repairs, timeout/error counts and end-to-end latency. Use the same total repair allowance as production. Test misleading but parseable diagrams and semantic source fidelity separately from keyword coverage. Count failures in denominators. A small 90-percent sample pass is not proven teaching quality. Report uncertainty and unmet thresholds without silently relaxing them; use current provider boundary for production changes.
