# Scoped lesson consumers and representation cache

Session selection/output, tutor requests and checkpoint skill resolution now pass the
learner into graph access. Tutor learning contracts and evidence independently verify
the supplied node; area membership/counts use the same scoped list. Challenge,
exercise and representation skill endpoints also pass scope. Playground lesson-origin
validation checks skill ownership before loading context.

Representation object lookup, cache reads and cached-kind enumeration are shared-only
without explicit scope. Cache store/invalidate require visible ownership before any
write. Rendering passes the session owner throughout. Preference recording validates
both representations and, for HTTP requests, their relationship to the route's skill
before emitting an event. No foreign content is accepted merely because its ID exists.

No private activation or content producer is enabled. This is not complete application
isolation: direct ORM reads, assessment ownership propagation, source/index/hosted
permissions and immutable relationship constraints still need the planned audit.
The static exercise catalogue still uses shared-only source lookup and must not become
a private-content producer accidentally. No model/provider, rubric or scheduling
policy changes are included. No frontend layout or interaction changes.

## Evidence
Ten focused tests pass, covering inherited private context, cached read/store/invalidate,
preference denial without events, HTTP selection/representation access and foreign tutor
request refusal before model calls; existing representation-history and playground
origin tests pass. Full backend suite: 1,582 passed. The new test also passes with additional HTTP preference and route-association assertions. Lint/types pass.
No live model call or learner-data write was used for verification. Existing UI evidence
is reused for this backend-only access change. Bounded code/pedagogy review found no blockers or majors; the broader isolation limits remain open.

CI on preceding sanitized head ed5e0e1 did not start: GitHub reports failed account
payments or a spending limit (run38409293675). Runtime jobs skipped, not verified.
