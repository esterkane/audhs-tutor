# Source currency: implementation prompts and acceptance gates

Status: planned, not implemented. Reconciles C01–C04 with E resource curation, M rights and authored
exports, and existing source-preserving saved answers. Keep active UX/reliability fixes ahead of this
queue. No new scheduler, dependency, hosted-model route or external provider is enabled by this plan.

## Existing evidence and distinction

DocumentVersion already has publication_date, ingested_at, content_hash and version. Saved-answer
source checks compare current local corpus hashes. Neither ingestion nor hash equality establishes
external currency, correctness or permission. Model licences are not document licences.

## C01a — Registry and evidence records

Prompt: Read AGENTS, architecture, data/event rules, source models and answer source checking. Use
resource-curation and state-reliability skills. Add a learner-scoped registry for explicitly selected
public source URLs, with document/version links and a separate append-only check record. Reuse the
existing publication date; track its precision/unknown status and evidence separately if needed.
Record check method, checked_at, last_success_at, observed revision/fingerprint, outcome and bounded
error code. Network defaults disabled. Separate transport checks from human semantic review and
rights evidence. No inferred publication dates or global trust upgrade. Propose the minimal migration,
typed API and local CLI; test migrations on a disposable database before live application.

Gate: tenant isolation, null dates, timezone validation, duplicate registry entries, failed checks not
advancing success, immutable document versions, backward-compatible backup/restore, no network on
read/startup, no credential-bearing URL persistence. Existing data is not mass-labelled verified.

## C01b — Explain freshness where sources are used

Prompt: Use learning-UX and tutor-evidence skills. Show a compact source status with checked date,
method and uncertainty in source details, lesson sources and saved answer evidence. Feed bounded
currency metadata through existing tutor context, not raw check logs. Start with user-selected
foundation/tooling/unknown categories and optional review intervals. Say review due rather than
wrong or expired. Keep local-copy unchanged distinct from upstream unchanged and reviewed correct.
Do not block reading merely because material is old. Preserve active-session source snapshots.

Gate: unknown/never checked/failed/changed/unchanged rendering, accessible details, fixed-clock date
boundary tests, no semantic endorsement from200/304/hash equality, no added confidence questionnaire.
One source-status vocabulary across fresh tutoring and saved-answer reuse.

## C02a — Explicit bounded checks and update candidates

Prompt: Reuse existing job lifecycle and safe-fetch controls. Add an explicit Check selected sources
operation, initially for reviewed repository revisions or feeds; page fingerprinting is a later adapter.
Validate schemes, DNS addresses and every redirect; reject credentials/private endpoints, bound size,
time and decompression, handle rate limits/cancellation. Fetch only approved public metadata; no
learner notes, private course titles or answers in requests. Store new fingerprints as idempotent review
candidates. Never overwrite source text, activate drafts, alter grades or invalidate an active session.

Gate:304, redirects to local addresses, DNS rebinding protection,429 Retry-After, timeout/partial result,
duplicate concurrent checks, cancellation/resume, failed-fetch fingerprint preservation and no secrets
in logs. Candidate acceptance invokes existing versioned ingestion through an explicit separate action.

## C02b/C03 — Opt-in scheduling and digest

Prompt: Only after manual checks pass, expose scheduling disabled by default. Show exact sources,
frequency, outbound data and Stop before enabling. Coalesce candidates into a capped digest at a
learner-chosen boundary; no interrupting the current block. Deduplicate by source/version. Discovery
uses reviewed public tags and enabled feeds, never private material as search text. Local relevance
scoring is a suggestion; the learner accepts resources and updates. Unavailable local scoring leaves
an unranked readable queue instead of silently calling a hosted model.

Gate: restart/idempotency, opt-out cancels future work, missed-run coalescing, quiet unchanged checks,
bounded queue, explicit accept/defer/reject, stable in-progress lesson, no accidental external requests.

## C04 — Optional workflow exercise

Prompt: Compare a workflow-tool adapter against the existing job runner using maintenance, local
resource cost and failure recovery. Keep any example an optional learning exercise. No mandatory
service, new credentials or background process solely to duplicate scheduling already supported.

## Cross-queue order and cost

M00/CM00 inventories rights/routing/export boundaries alongside C01a. M01/CM01 attaches evidence to
exact versions. Enforce reviewed rights decisions centrally before extending egress/export (M02/CM02,
A07/CM03). Similarity assistance M03/CM04 remains optional and cannot certify rights. AV00 assessment
supports a separate dependency-free SVG prototype reusing shared playback, after its adapter contract
and sensory gates; expressive models/3D remain deferred.

C01 metadata work requires no model or network. C02 cost is bounded HTTP/storage under explicit
controls. C03 may use installed local models only when measured accurate enough. Resource-dependent
notebooks need their own environment/compute review; a free link is not a zero-cost execution promise.

Each slice: implement, focused tests, source/code and pedagogy/UX review, document exact gates,
refresh private snapshot, commit/push private and sanitized variants separately. Generic plan/fixtures
only in sanitized history; source inventories, acquired material and private rights evidence stay private.
