# Answer-to-lesson binding foundation

Prepare private, read-only source identity for the planned G5 draft command.
Reuse owned, bounded answer ancestry resolution; use a distinct lesson binding and
hash current source checks separately from immutable generation lineage.
Changed answer, ancestor or reported source-check status conflicts during revalidation.
The status digest is not a hash of every current source byte or trust-policy rule;
changes that remain in the same status may not change it. Future command eligibility
must resolve current source/trust/permission rules independently in its transaction.
No API, inference, curriculum writes, events, UI, activation or permission grants.
Future writes must revalidate in their transaction and implement private ownership
before any publication; this helper alone is not a durable snapshot or access policy.

1562 backend tests and lint/types pass. Three new regressions cover owned read-only
identity, foreign/missing roots, source status changes and changed ancestry. Required
bounded code/pedagogy review found no blockers/majors; status-hash limits clarified.
UI/keyboard/mode behaviour is unchanged; no browser journey is claimed for this helper.
