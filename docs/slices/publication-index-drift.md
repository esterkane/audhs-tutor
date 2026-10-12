# Publication index drift guard

2026-10-12: a check invoked before staging validated the old index; later staging
introduced two source-specific generated API comments. Both repositories remained
private. Current generated descriptions are neutral, including their original
schema source. No credential or database finding was involved in this incident.

The publication check now rejects unstaged tracked changes in addition to scanning
all indexed blobs. Stage exact intended files, run the guard, then commit that same
index. Any further staging requires another check. Untracked local files are not
publication candidates until staged; this is not a general filesystem secret scan.

Four tests pass, including clean-index/dirty-working-tree rejection and forbidden
staged database despite cleaner unstaged content. Ruff and bounded code review pass.
No app/runtime change; no new browser, build or learning claim.

## History evidence and release boundary
A read-only scan of all locally reachable ref objects in the sanitized repository
inspected4232 blobs with the existing path/database/identifier rules. It found one
forbidden blob, in frontend/src/lib/api-types.ts: introduced by f19ad90 and removed
by b0fb93c. Current contents are clean, but historical contents are not. This is not
a comprehensive secret/license/content-rights audit, nor a scan of unreachable
objects, remote-only refs, forks or caches.

Keep the repository PRIVATE. Before future public release, prepare a newly audited
snapshot or explicitly authorized history cleanup while preserving the original
private history. No force push or history rewrite occurred in this slice.
