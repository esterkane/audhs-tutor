# Area catalogue metadata performance

Catalogue construction previously repeated regex construction, text normalization and ORM attribute access for every document-area pair, then rescanned documents for course counts and intersected large member sets. On a read-only metadata snapshot of 68,103 documents and 22 areas, the original membership loop alone took 19.752 seconds.

The catalogue now queries only the four needed document metadata columns, creates immutable tuples on the event loop, and performs matching/aggregation in `asyncio.to_thread`. No session, ORM object or live database connection enters the worker. It compiles each area's existing token/plural/stem expressions once, uses a literal substring prefilter before regex searches, caches course matches, groups identical normalized title/section/lecture and course metadata with multiplicity, and accumulates counts/course names/related areas directly. Area and related-title ordering, raw term metadata, source matching semantics and learner-scoped nonrejected draft selection remain unchanged. There is no persistent cache or new invalidation requirement.

Matching expressions are shared with the original matcher, retaining casefolding, literal escaping, Unicode word boundaries, explicit legacy stems and the existing allowed English plurals. The helper remains lazy for ordinary `match` callers. A metadata match is still a proposal, not evidence quality. Source-role exclusion and trusted/latest/nonduplicate passage filtering remain in the untouched source/excerpt paths; catalogue counts keep their previous broader metadata meaning.

## Evidence

Local read-only SQLite `mode=ro` snapshot, CPython 3.12.14, Darwin arm64, 68,103 documents and 22 areas: optimized aggregation took 0.623 seconds in one run; a subsequent exact equivalence run took 0.643 seconds versus 20.722 seconds for the reference membership loop. Per-area document counts, sorted course lists, related-area sets and assigned-document totals were equal; total memberships were 73,021. Input projection/load time is excluded, and these are sequential single trials, not an endpoint latency SLA. No corpus text, private course names or data files are included here. No live database was written.

16 focused tests cover catalogue parity, duplicate metadata multiplicity, punctuation/Unicode/word boundaries/plurals/stems, no areas, source filtering and selection. A real async catalogue regression blocks the worker on a threading event, confirms the event loop remains available to release it, checks plain tuple snapshots and excludes another learner's/rejected drafts. Existing area excerpt/source-trust tests remain green. Targeted Ruff/format and configured backend mypy pass. Running mypy from repository root without backend configuration initially exposed unrelated missing third-party stubs; the configured backend invocation succeeds.

Limits: metadata SELECT/materialization still happens before worker aggregation; thread execution shares the Python GIL and is not a hard real-time guarantee. Concurrent catalogue calls do independent work. Live endpoint and broader page responsiveness need integration verification after restart; no claim of fixing every Home latency source. Independent review and dual publication belong to the integration owner.

## Integration verification

After restarting the owned local backend, concurrent read-only requests returned: /api/areas 0.926s (22 areas), /api/health 0.051s, /api/skills 0.088s. These are single local observations, not an SLA. Independent code and pedagogy reviews found no blockers or majors.
