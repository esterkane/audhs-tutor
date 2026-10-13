# Grader criterion transport proposal

Status: reviewed design; isolated adapter implemented, not enabled. 2026-10-13.

## Problem and boundary
The existing grader requires the model to repeat each complete rubric string. A local diagnostic shortened those strings and failed validation. A rejected exact-copy/output-budget experiment fixed structure but falsely passed a compound requirement. Installed 27B with the unchanged contract also returned no accepted outputs. See ../slices/private-transfer-grader-evaluation.md. Identity transport and semantic quality are separate gates.

## Proposed contract
Use a separate internal model-response schema, versioned with a new prompt. Each invocation assigns opaque request-local IDs c1..cN to the immutable rubric snapshot already supplied to that invocation. The prompt supplies every complete criterion with its ID as escaped data; no rubric text is removed from model input. Output rows contain criterion_id, strict boolean passed, and nonblank evidence. Top-level misconception, bounded confidence, feedback and next_step remain as today. Reject unexpected schema fields.

Require exactly one row for every supplied ID. Reject unknown, duplicate, missing or empty IDs and blank evidence; never infer identity from order, similar strings, or an abbreviated label. Reordered complete rows are acceptable. Only after validation map IDs to the original full server-owned criterion text and order, constructing the existing GradeResult. No model-supplied text becomes the rubric identity. IDs are ephemeral within the invocation, not persistent assessment identifiers.

Preserve the existing rejection of duplicate normalized rubric descriptions. Preserve request/assessment snapshot binding, review eligibility frozen before inference, execution claim recovery, existing grade persistence and public API schemas. The new internal type must not accept legacy GradeResult as a fallback. Historical stored results remain unchanged. No migration, UI redesign, provider/routing change or paid call is required.

Retain the existing output limit for the first isolated comparison; shorter IDs should reduce redundant output. Do not automatically enlarge token budgets or retry semantic failures. Preserve provider/gateway accounting and limits. A rejected output follows the current unavailable-grade path and cannot award evidence.

## Implementation and release gates
1. Pure adapter tests: reordered rows map correctly; missing/duplicate/unknown IDs, coercible booleans, blank evidence, extra fields and duplicate rubric identities fail closed. Snapshot mapping must not mutate caller data.
2. Gateway boundary tests verify full escaped rubric content, prompt version and internal response schema. Recovery tests verify only converted GradeResult is persisted and no writes follow invalid output. Existing deterministic graders and public schemas remain unchanged.
3. Isolated local evaluation using the four retained synthetic cases plus negation/qualification contrasts. Record structural acceptance, criterion decisions, evidence fidelity, corrective feedback and latency separately. No automated accuracy claim from schema acceptance.
4. Code and pedagogy reviews before enabling the production call site. A false pass on the known compound requirement blocks deployment even if other cases improve. If this gate fails, retain the adapter as experimental or remove it, leaving runtime unchanged.
5. Relevant backend tests, lint/type checks and unchanged-runtime regression reuse. Browser checks are needed only if user-facing behavior changes; no new visual or accessibility claims from backend checks.

## Limits and non-goals
IDs establish correspondence, not factual correctness, calibrated confidence, valid evidence quotes or learner understanding. Do not add task-specific keyword rules, silently split the reviewed rubric or change scoring to make the sample pass. General quote validation or semantic verification needs its own evidence and contract. Explicit task/rubric review and lesson activation remain separate from model checking and independent competence.

## Foundation evidence
Code and pedagogy design reviews found no blocker/major. The isolated `orchestrator/grader_transport.py` adapter implements immutable snapshot mapping and strict model-response validation; it has no production caller. Sixteen focused tests pass, with targeted Ruff and mypy passing. This establishes correspondence behavior only. Prompt/gateway integration, recovery tests, local semantic evaluation and deployment gates above remain open. No frontend or runtime behavior changed.

## Local gate result
The first isolated six-case sample accepted all ID mappings but failed semantic checks, including crediting a claim opposite to the criterion. Deployment is blocked by the stated quality gate. See ../slices/private-transfer-grader-evaluation.md. The experimental prompt is not selected by the runtime prompt loader; the adapter has no production caller.
