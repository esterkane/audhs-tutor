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

## Hosted project tutor evaluation, 11 November 2026

The eight-case run used fresh synthetic sessions, PostgreSQL 17.11 and manual review of the complete English and German answers. Five answers met all criteria. Both NULL comparisons, both Read Committed examples and the English write-skew example passed.

Both row-security questions reached a generic incident response and omitted the requested comparison. After the routing change in `10deb29`, targeted retests covered all three outcomes in both languages. The German write-skew answer initially omitted the second commit failure and the final worker count. A targeted retest after the worked-comparison change in `6608689` included both observations and the limits of that particular schedule.

These results span three application versions. A release-wide eight-case result still requires running the complete set on the same revision. The static case manifest remains a specification. The run-specific scores come from private review receipts.

### Search planning and response time

Two targeted trials used the same English and German row-security questions. Both required complete answers, faster responses in each language, at least 15% less combined waiting time, and estimated cost no greater than baseline. The baseline pair took 55.828 seconds. A broader first query took 60.332 seconds. Allowing a second independent query in the first planning round took 55.048 seconds. In that trial the model still requested one initial search in each language. English improved by 2.261 seconds, while German took 1.481 seconds longer. Both trials produced complete answers but exceeded the baseline cost. Both changes were reverted.
