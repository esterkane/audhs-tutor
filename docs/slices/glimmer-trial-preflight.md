# Glimmer hosted trial: offline preflight

Owner approved a synthetic-only OpenRouter comparison up to $1. This first slice
validates the frozen eight-case teaching artifact and prepares provider-pinned
requests without reading credentials, opening a database or calling any service.
There are no learning events, UI, modality, mode/energy or accessibility changes.

Run `python3 scripts/glimmer_trial_preflight.py`. Only the exact reviewed synthetic
artifact is accepted by SHA-256, and each recorded prompt hash is verified. Requests
pin deepinfra/bf16, require supported parameters and disable provider fallback.
The original 900-token output cap remains for comparability.

The sequential budget reserves the complete advertised 131072-token context as
input plus 900 output tokens, at the verified rates and a conservative 5.5% fee.
This is $0.042623688 per request or $0.340989504 for eight, not a prediction of actual
spend. It depends on the endpoint honoring its advertised caps/rates; execution must
revalidate those. Unknown/invalid cost retains its reservation and halts. Unexpected
excess cost is recorded and halts. No automatic retries or concurrent reservations.

Verified catalog: https://openrouter.ai/api/v1/models/meta/muse-glimmer-30b/endpoints
on 2026-10-12: DeepInfra BF16, context131072, max completion16384, $0.30/M input,
$1.20/M output, supports max_tokens and reasoning parameters. The report's earlier
Together FP8 statement refers to Together direct, not this DeepInfra endpoint.

## Validation
12 offline tests pass, covering artifact tampering, pinned routing, reservation
exhaustion, overlapping reservations, missing/nonfinite/negative usage, reconciliation,
excess billing and ceilings above owner approval. Ruff and strict script mypy pass.
CLI succeeds on the Mac's system Python with postponed annotations. No browser/build
rerun: application code is unchanged. Tests do not prove provider behavior or teaching
quality. This is a preflight, not an executable hosted integration.

## Remaining before execution
Credential; current rate/cap checks; fake-tested streaming transport with first visible
text timing, usage and reasoning accounting; persistent exclusive campaign journal
before network sends so process restarts cannot reset the approved budget; timeouts
and ambiguous outcomes halt; provider identity verification; semantic review of all
answers. Reuse provider/gateway boundaries for integration. No automatic routing
promotion. Production and the local diagnostic remain unchanged.

## Review
Bounded code review found no blockers or majors. This review does not establish
paid execution readiness.

The subsequent hosted trial slice increases the conservative reservation to the
endpoint maximum16384 output tokens, including potential reasoning, even though
requests stay at900. The revised eight-call bound is $0.497811456. See
[hosted trial](glimmer-hosted-trial.md) for transport, persistent journal and results.
