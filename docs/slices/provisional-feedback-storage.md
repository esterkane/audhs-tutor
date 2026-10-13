# Provisional feedback storage foundation

2026-10-13. Added separate learner-owned provisional_feedback table and migration a71f2039c4de. Stores claim/session/assessment identity, revision lineage, policy/content fingerprint, exact answer and private binding/model/outcome snapshots. No score/mastery/review columns. One record per claim; update trigger prevents mutation, insert trigger validates claim/session owner and same-owner/content revision lineage. No production writer or routing switch yet.

Backup recognizes and validates exact guard definitions; post-upgrade restore checks stored ownership relationships even if an archive bypassed insert guards. Metadata-driven export and wipe include records; deletion remains permitted for learner wipe. No live migration was run.

Validation:24storage/backup/migration tests passed with a clean exit under PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and pytest_asyncio.plugin. Standard initial run passed23assertions then crashed in native library teardown; plugin-isolated rerun succeeded. Final4storage tests rerun after test cleanup. Ruff and mypy pass. Code review found no blockers/majors in the storage boundary. This establishes neither runtime policy enforcement nor model accuracy.

Next: implement owned persistence under request lock, validate assessment visibility and immutable binding content, adopt provisional outcome union across recovery/answers/revisions, and integrate UI. Historical assessed results remain untouched. No model calls or dependencies added.
