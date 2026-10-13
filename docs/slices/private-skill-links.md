# Private skill links

Learners must not resolve another owner's private skill title or assessment dimensions through
competency views, reminder promotion/Undo, or historical experiment labels. Existing shared
and owned access and missing legacy experiment-unit behavior are preserved. No new event,
model call, learning policy, mode/energy behavior, or UI is introduced; accessibility is unchanged.

## Implementation and acceptance

- Competency mastery/detail refresh the node before checking its owner; foreign nodes return404.
- Reminder promotion (including the legacy route) rejects foreign links before mutation.
- Undo refuses restoration of an inaccessible historical link with the existing conflict response.
- Experiment labels resolve only visible skills, retaining the existing unresolved-ID fallback.
- Regression coverage: direct competency reads, missing legacy IDs, both promotion routes,
  action-count/state preservation on denial, historical Undo and experiment title redaction.

## Verification

Full backend suite:1585 passed (three existing dependency warnings), focused suite:25 passed,
`make lint` including Ruff, mypy, frontend TypeScript and ESLint passed. Bounded code/pedagogy
review found no blockers or majors. Logs: `/tmp/audhs-private-links-full.log`,
`/tmp/audhs-private-links-focused2.log`, `/tmp/audhs-private-links-lint.log`.
Backend-only change; no visual/keyboard behavior changed.

## Remaining scope

This is not complete private-content isolation. Lower-level competency state/evidence writes,
experiment assignment/aggregate isolation, immutable ownership/relationship constraints,
retrieval/permission boundaries and private activation lineage remain separate gates.
Private producers remain disabled. No assessment qualification or learning evidence is created.
