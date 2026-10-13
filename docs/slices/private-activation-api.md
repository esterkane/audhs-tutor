# Private activation API

The learner needs an exact draft preview and recoverable activation receipt before UI controls
can be connected. This slice adds owned preview/read routes and an explicit, bounded, idempotent
command route. No new learning events, grading, scheduling, mode/energy or accessibility behavior.

- GET /api/lesson-activations/drafts/{draft_id}/preview reads one snapshot and checks the same
  content validation as activation, current source binding and draft state. It returns title,
  counts, source warnings and exact command identity; it does not return raw origin snapshots.
- Already activated drafts return their receipt and no new command. Changed source history,
  invalid content and discarded drafts return issues with no actionable command.
- POST /api/lesson-activations/commands requires Idempotency-Key and enforces 4096 actual streamed
  bytes. Safe errors do not echo private validation input. The existing atomic repository owns
  writes and rechecks state; preview is never an authorization bypass.
- GET /api/lesson-activations/{activation_id} reads the owned immutable receipt. Missing and foreign
  IDs return equivalent responses. Local single-owner access remains distinct from multi-user auth.
- The unchanged validation body is extracted into a shared read-only helper to prevent preview
  and execution drift. No source permissions, factual checks or review qualification are inferred.

Verification: 1630 full backend tests pass (three dependency warnings), plus 23 focused
command/API tests in both checkouts. Generated API types, lint/types and publication guard pass.
Required code and pedagogy reviews found no blocker/major. Snapshot verified unchanged.
UI remains next; no browser verification or additional live lesson activation is claimed.
The UI must treat receipt-only responses separately: default zero preview counts and unknown
grounding are not measurements of the activated lesson. Replace activation-unavailable draft
copy only when explicit preview, confirmation and durable retry recovery controls are connected.
