# Provisional feedback rollback preservation

Integrated regression testing found that downgrading from a populated provisional-feedback database dropped its table before an older migration refused to remove populated lesson history. SQLite did not restore that dropped table. This is a recovery defect, not a change to learning decisions.

Bounded fix: refuse downgrade at the provisional-feedback migration before any DDL when feedback exists. Empty databases may still downgrade. Verify rows, schema, revision and immutability guards survive rejection on disposable databases. No live database downgrade is authorized or needed.

## Verification

- Full backend regression initially reported 1693 passed and four failures: two stale backup-fixture revision declarations, the expected-table list missing provisional feedback, and the destructive downgrade defect above.
- Corrected all four failures; all 22 tests in the four affected storage/schema modules pass, including three new downgrade cases. This is a targeted rerun, not a claim that the original full run passed.
- Full frontend regression: 139 files, 717 tests passed. No frontend files changed in this slice.
- Full lint, formatting and backend/frontend type checks pass. Independent code review found no blockers or majors. No learning decision, scheduling, UI or model routing changes.
- Activation and lesson-history guards remain independently tested at their own revisions so the new guard cannot mask regressions in older migrations.
- The full isolated browser regression is still in progress at this checkpoint; no complete-suite claim. Visual/keyboard/responsive evidence for unchanged session flows remains in their existing slice records.
- Latest remote CI run 38473143275 did not start runtime jobs because of the account payment/spending-limit check. Local verification does not resolve that external gate.

No live database downgrade was performed. Existing saved feedback remains advisory under the approved policy.

