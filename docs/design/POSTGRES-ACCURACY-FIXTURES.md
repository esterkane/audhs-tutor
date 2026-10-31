# Executable PostgreSQL accuracy fixtures

Use official, versioned documentation together with database observations when evaluating
Supabase/PostgreSQL explanations. Documentation establishes general semantics; a synthetic
fixture establishes only its own behavior, never a production incident's cause.

Run from WSL/Linux, with Docker and the already installed Supabase PostgreSQL 17 image:

    python scripts/postgres_accuracy.py

The command resolves the local image to an immutable ID and refuses image downloads. It
creates its own randomly named, labelled container with no network, no published ports,
a read-only root, bounded memory/CPU/processes and temporary in-memory data. It never
accepts a project connection URL or executes learner/model SQL. Cleanup checks the exact
fixture label before removing the container. Startup, SQL and barrier failures abort the
run instead of becoming a passing result. No application tables or sessions are opened.

The JSON report includes the actual server version, image ID and these observations:

- UPDATE USING excludes an ineligible existing row (zero updated rows).
- UPDATE WITH CHECK rejects an invalid proposed row and leaves stored data unchanged.
- Missing UPDATE privilege also produces SQLSTATE 42501; that code alone is not a diagnosis.
- Two transactions that each observe two available workers can commit disjoint withdrawals
  under Repeatable Read, leaving none available. The scripted Serializability schedule
  rejects the second commit with SQLSTATE 40001 and retains one available worker.

A snapshot preventing phantom reads does not establish serial equivalence. Serializable
applications must handle possible failures by retrying the complete transaction and its
statement/value-selection logic, while accounting for external effects. These fixtures do
not prove automatic retry safety, all possible schedules, JWT identity, REST authorization,
view security or arbitrary generated SQL correctness.

The fixture version is PostgreSQL 17, matching its image, rather than the mutable current
manual. References:

- https://www.postgresql.org/docs/17/sql-createpolicy.html
- https://www.postgresql.org/docs/17/transaction-iso.html
- https://www.postgresql.org/docs/17/mvcc-serialization-failure-handling.html

For the executable success/error/cleanup checks (explicit opt-in; no image pull):

    cd backend
    AUDHS_POSTGRES_ACCURACY=1 .venv/bin/python -m pytest tests/test_postgres_accuracy_command.py -q

Normal test runs exercise failure barriers and ownership checks without requiring Docker.
Use actual saved answers, matched source passages, complete outputs and session checkpoints
for a model comparison; keyword matches or this fixture's success alone cannot certify an
answer's causal explanation or citation entailment. Keep model transcripts and learner data
out of publication. Compare first-token and complete-response latency separately from SQL
or retrieval setup, and do not infer a generation speedup from shorter incomplete answers.
