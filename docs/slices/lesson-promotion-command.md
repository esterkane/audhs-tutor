# Atomic private lesson-draft creation

An explicit bounded command supplies the domain, objective, explanation, worked
example, transfer question, criteria and prerequisite slugs. Source identity is
re-resolved under BEGIN IMMEDIATE; caller ownership/provenance fields are rejected.
Creation saves the draft, immutable promotion and private raw lineage atomically.
Same-key/body retries return the original creation receipt, not current draft state;
changed-body reuse conflicts. Existing edits are never overwritten by a replay.
No inference, activation, evidence, permission upgrade or source deletion occurs.
Unknown history remains private/unverified; no source passages are invented for the
edited content. Shared publication stays blocked by the persisted promotion link.

This kernel command has no API/UI consumer yet. Next transport must cap streamed
bytes before parsing, preserve original retry keys/bodies and label activation limits.
Private publication ownership and source-policy enforcement remain separate gates.
Validation: 1569 full backend tests pass; a subsequently added storage-failure regression
also passes in the four-test focused run. Lint/types pass; required bounded review found
no blockers/majors. Tests cover concurrent duplicate requests, changed-body conflicts,
replay after edits/source changes, foreign access, invalid input and rollback when
snapshot insertion fails. No frontend behaviour changes; no browser claim for this kernel slice.
