# PostgreSQL factual case manifest

The eight cases in `evals/cases/project-postgres-causal.json` pair English and German
questions across four families: NULL comparisons, Read Committed updates, RLS boundaries
and write skew. Both languages share factual criteria; wording differences must not change
the expected semantics. The prompts are synthetic developer-authored cases, not learner data.

Each required claim identifies versioned PostgreSQL 17 documentation and, where relevant,
an independent observation from `scripts/postgres_accuracy.py`. Forbidden claims record
specific overgeneralizations or invented explanations. They are reviewer criteria, not
keyword lists to run against model output.

## Implemented fixtures versus executed evidence

The existing oracle implements RLS USING/WITH CHECK/missing-privilege observations and
the fixed Repeatable Read/Serializable write-skew schedule. The manifest binds to those
report fields. An implemented binding means the capability exists, not that it was run
successfully for this evaluation; retain the actual versioned report and its hash.

The NULL truth table and concurrent absolute-versus-relative update observations are now
implemented in the same isolated oracle. All thirteen current bindings identify actual
report fields; future planned bindings must still keep report_path null. Availability
does not establish successful execution: a review must use a recorded report from its
own verified fixture version or explicitly label execution evidence unavailable.

The NULL fixture evaluates the four ordered cases in SQL and preserves JSON null versus
false. The Read Committed fixture records both initial reads of 100, observes that T2 is
blocked by the exact T1 backend PID before releasing T1, and checks returned and committed
balances of 80 for absolute assignments and 70 for database-side subtraction. A missing
lock-wait barrier or early completion aborts instead of claiming the schedule occurred.

The fixed Serializable fixture rejects the second commit. Its victim and timing must not
be generalized to every schedule. RLS observations concern the specified ordinary role;
SQLSTATE 42501 does not uniquely identify a production incident's cause.

## Review contract

The manifest starts as `not_run`. A future private review receipt must identify the case,
manifest and transcript hashes, model settings, oracle report hash or unavailability,
reviewer and time. Each criterion needs an answer excerpt, matched source passage or
oracle observation, verdict (`pass`, `fail`, `unresolved`) and reason. Missing evidence or
review stays unresolved. Keep all answers, sources and histories privately, without
changing acceptance, progress, mastery or model routing.

JSON validity, keyword presence, citation markers, a passing fixture and agreement between
models cannot alone establish that a generated causal explanation is correct. These tests
validate the manifest's integrity, not a model's factual accuracy. There is no automatic
semantic scorer or paid model call in this slice.

## Offline validation

Run from `backend`:

    .venv/bin/python -m pytest tests/test_project_accuracy_cases.py -q

Tests check language pairing, common claim criteria, source versions, distinct case/claim
identities, explicit planned/implemented separation and the existing oracle's report-field
shape via source AST inspection. Corrupted/overclaimed manifests are rejected. They do not
start Docker, connect to a database or access held-out results.

Verification: 23 offline tests passed with three explicit Docker tests skipped. With the
already installed PostgreSQL 17 image, all 26 tests passed, including actual NULL/locking
observations, report-to-manifest binding checks and container error/cleanup cases. A separate
report run recorded PostgreSQL 17.11, both expected balance outcomes and both lock waits;
the labelled fixture container was removed. Ruff lint and format checks passed. No model
was called and no learner database was opened. The manifest remains not_run for model
qualification; executing a SQL oracle does not grade a generated answer.

Next: freeze a bounded real-provider campaign through the actual project gateway and
review complete answers against both documentation and these measured observations.
