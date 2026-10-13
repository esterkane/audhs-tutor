# Private lesson activation: access and lineage contract

Status: proposed implementation architecture. Activation remains disabled until the
complete boundary is implemented and verified. No permission or review is inferred.

## Repository audit (2026-10-13)

- `db/models.py`: Assessment has nullable owner_learner_id; SkillNode,
  LearningObject and Representation do not. SkillEdge connects global node IDs.
- `kernel/question_state.py`: assessment visibility already distinguishes shared
  from owned rows. Reuse that semantic rule, not a second assessment policy.
- `kernel/skill_graph.py`: get_node, get_node_by_slug, all_nodes, all_edges,
  prerequisites, topological_order and learning_object_for lack learner scope.
  next_skill accepts a learner but depends on those global reads.
- `api/skills.py`: list, map, direct skill and skill-targeted mutations consume that
  graph. Filtering only the list or Home would leave direct-ID exposure.
- `kernel/representations.py`: object_for_skill and representation reads/writes
  operate on object IDs without an ownership boundary.
- `kernel/curriculum.py`: publish_draft upserts by globally unique slug and finds
  existing objects/assessments. It must not be reused unchanged for private activation.
  The existing LessonPromotion guard correctly refuses such publication.
- Further consumers include competency, task_reviews, exercises, listening,
  practice, parking_actions, playground, challenge, grader and session continuation.
  These are audit targets, not a claim that the inventory is exhaustive.

## Schema and ownership

Use a nullable immutable owner_learner_id on SkillNode: null retains existing shared
content; non-null is visible only to that learner. Do not infer ownership for legacy
rows. Private lesson activation creates fresh private nodes and never overwrites a
shared node by slug. Keep global slug uniqueness with server-generated private slugs;
slugs are identifiers, never authorization.

LearningObject and Representation inherit access through their skill/object chain.
Every read/write must resolve that chain before returning content. Assessments for a
private node must have the same owner; a private assessment on a shared node retains
its existing behavior. Enforce these relationships at storage boundaries, including
updates/restores, not only through the activation API.

Edges may connect shared prerequisites to a private target, or same-owner private
nodes. A shared target must not depend on a private node; cross-owner private edges
are invalid. Filter both endpoints before exposing graph structure or counts.
Private activation must not mutate shared curriculum metadata or knowledge areas.

Persist an immutable activation record linking learner, promotion, exact draft
version/payload hash and every created node/object/assessment ID. Keep original
answer/source lineage separate from edited teaching content. Preserve historical
versions; later edits must not silently rewrite published lesson or review evidence.

## Read and write boundary

Introduce explicit learner-scoped graph/object access helpers. Missing learner scope
must mean shared-only, never all rows. Missing and foreign IDs have the same public
response. Review all direct ORM access and joins, including:

1. Home/next skill, map, prerequisites, topic/course counts and area suggestions.
2. Lesson retrieval, representation caches, voice context, grading and task review.
3. Session start/resume, saved targets, assessment selection and exercises.
4. Search/retrieval indexes, cached answers and derived visual inputs.
5. Export/backup/restore/wipe and diagnostics returning content.

Do not rely on process-wide current-user state or a UI filter. Scope cache keys and
index queries; a foreign row must not influence ranking, counts or fallback content.
Keep private lessons out of shared indexes until an owner-filtered implementation is
verified. Local ownership does not confer hosted-model or public-export permission.

## Backup and wipe

Existing learner-table discovery is insufficient for owner_learner_id nodes and
inherited objects/representations. Add explicit dependency-ordered deletion of owned
activation links, private assessments/rubrics where no remaining references exist,
representations, objects, edges and nodes after learner evidence/recovery references
are removed. Preserve shared prerequisites and every other learner's records.
Test the actual foreign-key graph, not a hard-coded happy-path subset. Restore must
revalidate ownership relationships and fail atomically on cross-owner references.
Learner backups retain derived teaching content; raw promotion snapshots keep the
existing full-private-backup distinction. Public exports remain forbidden by default.

## Activation command

Explicit owner action with expected draft version and durable request key. Reserve
one transaction, verify draft/promotion ownership and status, validate prerequisites,
freeze payload/lineage and create all content plus activation receipt atomically.
No model/network work inside that transaction. Same key/body returns the original
receipt; changed payload conflicts. Concurrent different keys must not activate the
same draft twice. Storage failure leaves no partial curriculum.

Source status changes require an explicit current review path; they must not silently
upgrade permissions or erase historical lineage. Missing sources remain disclosed.
Activation is neither a task/rubric review nor competency/FSRS evidence. The synthetic pilot received a separate explicit activation decision; that does not
authorize activation of other drafts or qualify its persisted assessment.

## Bounded execution sequence

1. Add ownership schema, immutable constraints and owned graph/object helpers;
   keep the publication guard and private producers disabled.
2. Migrate every runtime consumer, cache and search boundary. Add cross-owner
   tests for direct IDs, indirect joins, resume and aggregate/list leakage.
3. Implement immutable activation links, transactional command and backup/wipe
   ordering. Verify retained historical references and forbidden owner changes.
4. Add explicit activation UI, lost-response recovery and provenance display only
   after all preceding gates pass. No automatic activation or assessment review.

## Acceptance gates

Use shared fixture plus learners A and B, private content for each and deliberately
invalid cross-owner edges/assessments. Verify shared behavior is unchanged and each
learner can study only their own private lesson. Exercise list/map/direct reads,
planning, grading, cached representations, voice context, retrieval and resume.
Verify foreign IDs cannot change state or expose even titles/counts. Test concurrent
activation, version conflict, failure between writes, lost response, backup/restore,
wipe, migration and refusal of downgrade with populated private content.

Browser gates: explicit preview/activation, inactive versus active status, exact
source restrictions, keyboard and narrow layout, stop/retry, Back/Forward/reload.
Use disposable data. Passing fixtures establish access/transaction behavior, not
teaching effectiveness. Owner usability, content approval and exact assessment
qualification remain separate.

## Review
Bounded architecture review found no major gap; its explicit wipe-discovery concern
is incorporated above. This is a plan, not proof that private activation is safe yet.


## Storage implementation update — 2026-10-13

Revision52443d30fac9 adds immutable skill/assessment ownership, inherited owner protection
on object/representation reparenting, and edge/assessment relationship guards. Migration refuses
invalid existing relationships; backup validation recognizes guards by revision and checks their
definitions, then rechecks relationships after upgrade. See slices/private-content-storage-guards.md
for verification. These constraints do not authorize callers; scoped consumers, remaining
experiment/retrieval boundaries and activation lineage are still required before the producer opens.
