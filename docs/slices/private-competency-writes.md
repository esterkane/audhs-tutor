# Private competency writes

Prevent foreign private skill IDs from reaching competency evidence, refresh or state reads.
Reuse the existing refreshed-node ownership check before reads or writes. Shared and owned
skills retain identical scoring, decay, confidence and scheduling behavior. No UI, mode/energy,
model or accessibility behavior changes. Authorized evidence retains its existing event contract.

## Verification

Full backend suite:1586 passed (three dependency warnings);10 focused tests passed.
`make lint` passed Ruff, mypy, TypeScript and ESLint. Bounded code/pedagogy review
found no blockers or majors. Logs: `/tmp/audhs-competency-write-full.log`,
`/tmp/audhs-competency-write-focused2.log`, `/tmp/audhs-competency-write-lint.log`. The focused regression checks
both commit modes, denial before evidence/state/event creation, shared/owned refresh, and missing
legacy-unit empty reads. Existing kernel tests cover scoring and refresh behavior.

## Storage audit and remaining work

This is an application-level guard, not a storage invariant. Direct SQL can still bypass it.
Immutable ownership and relationship constraints require coordinated migration, ORM create_all
hooks and backup validation. backup._check_snapshot_schema uses an explicit trigger allowlist;
new triggers must be required by schema revision while older snapshots remain upgradeable.
Restore must also validate existing relationship rows after upgrade: installing triggers alone
does not repair or reject preexisting invalid rows. Current access regression fixtures deliberately
create invalid relationships; retain that defensive-read coverage explicitly when storage guards
land rather than silently dropping it. Experiment assignment/aggregate isolation, inherited
object relationships and private activation lineage remain open. Private producers stay disabled.
