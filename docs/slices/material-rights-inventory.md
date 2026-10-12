# M00 — source rights and output boundary inventory

Status: source-code inventory completed 2026-10-12. M01/M02 design and enforcement
remain unimplemented. This is a technical inventory, not a legal determination or
permission to transmit/distribute any particular source. No learner records were
read, classified, changed or deleted for this inspection.

## Existing boundaries and gaps

| Boundary | Inspected implementation | What it establishes / what is missing |
| --- | --- | --- |
| Imported source | `backend/app/db/models.py`: Document, DocumentVersion, Chunk, ChunkProvenance; `knowledge/provenance.py` | Location, version/hash, ingestion date, citation context and trust tier exist. Document/version permission evidence, licence scope and attribution obligations are not represented by these fields. |
| Model licence | ModelRegistry.licence in `db/models.py` | Describes a model; it is not a licence for material in the model input or generated output. |
| Tutor context | `orchestrator/context.py`, `orchestrator/playground.py` | Sources/work are separated from instructions and source snapshots are retained. Untrusted-data handling prevents instruction authority; it does not decide permission to transmit. |
| Hosted inference | `models_ai/gateway.py`: complete, _reserve; `models_ai/provider.py` | Route/readiness/provider and budget checks precede inference. No source-rights eligibility envelope is consumed here. Local-first is a preference/route, not proof that all fallback paths are local. No claim is made that a particular private passage has actually been sent. |
| Saved/derived answers | TutorAnswer.request_json and metadata; `orchestrator/representations.py`, `orchestrator/workspace_provenance.py` | Work, citations and hashes support traceability. Citation warnings and cached answers do not certify rights or correctness. Derived prose/code can contain source text; it needs lineage rather than an inferred shareable flag. |
| Learner export | `db/portability.py`: export_learner; `scripts/export.py` | Exports learner-scoped rows plus owned assessment/rubric/profile. Those rows can contain source-derived material. Ownership of a row is not an implemented distribution eligibility check. |
| Private backup | `db/backup.py`, `backup_crypto.py`, `scripts/backup.py` | Learner scope removes raw chunks/provenance/index/checkpoints; derived material can remain, as the code documents. Full scope is private recovery. Encryption protects an archive; neither scope is a sanitized public export. |
| Git publication | `scripts/check_publication.py` and separate sanitized checkout | Checks staged paths, database signatures and prohibited identifiers. This is a publication guard, not general source-licence analysis or proof that every arbitrary quoted passage is cleared. Both repositories currently remain private. |

## Required separations

Keep these as distinct facts: access, local copying, transformation, hosted
transmission and redistribution. A public URL, paid subscription, ingestion success,
owner trust score, unchanged hash, citation or model licence cannot substitute for
an explicit recorded decision about another action. Unknown remains unknown; do
not mass-label existing records allowed or forbidden based on this inventory.

An eventual policy envelope must accompany mixed content, including learner text,
code, notebook output, retrieved chunks and saved answers. The most restrictive
applicable decision cannot disappear through summarization or cache reuse. Merely
scanning the final output for names is insufficient to establish lineage.

## Next bounded design: M01 alongside C01a

Propose version-linked evidence records, retaining:

- Exact source/document-version identity, evidence origin and recorded date.
- Observed licence text/reference and attribution information, with unknowns explicit.
- Separate action-specific policy decisions and their basis; user assertions remain
  labelled assertions rather than verified source terms.
- Original, source-derived and AI-assisted lineage, including mixed/unknown inputs.
- Append-only decision history and policy version; corrections supersede rather than
  erase prior evidence. Source content/version stays immutable.

Before a migration, resolve shared document versus learner-specific decision scope,
backup/restore compatibility and the policy for unknown evidence. Do not introduce
network checks, automatically inspect authenticated accounts, or change curriculum,
mastery or gating as part of metadata work.

## M02 enforcement acceptance, after the policy is agreed

Use the existing model gateway and explicit export boundaries, including streaming,
structured calls and fallback attempts. Apply eligibility before reserving/sending a
hosted request; preserve a capable local route and give an honest unsupported state
when none can satisfy the task. Do not silently trim required source context to make
an ineligible request eligible. Keep private recovery distinct from public export.

Test mixed sources, missing/version-mismatched evidence, nested notebook code/output,
cached answers, fallback and stream paths, revoked decisions, restored backups and
cross-learner isolation. Test that rejected egress makes zero provider calls and
that permitted local work remains usable. These are future acceptance requirements,
not implemented protections or completed tests.

## Evidence limits

Read-only inspection of the named code and existing source-currency/learning-material
plans. No new dependency, schema, endpoint, runtime behavior or rights classification.
No browser or runtime regression suite rerun for this inventory. Private acquisition
scripts/material remain untouched; inventory contains generic code boundaries only.
