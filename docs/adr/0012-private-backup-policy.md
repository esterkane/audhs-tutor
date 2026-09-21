# 0012 — Private recovery and encrypted backup dependency
Date: 2026-09-21
Status: Proposed

## Context
Owner requested resolution of the dependency decisions in IMPROVEMENT-PLAN and execution of the local setup and commit plan.

## Decision
Keep learner-only backup as the default. Explicit full backup may include purchased corpus text solely for private recovery on the owner’s machine; it is not a sharing/export feature. Approve cryptography for authenticated, password-based encrypted backups, with a versioned envelope, bounded resource use, wrong-password/corruption tests, and no stored password. Existing ZIP backups remain clearly marked unencrypted until an encryption implementation and round-trip tests land. Do not use whole-file Fernet for unrestricted large course archives.

## Consequences (positive / negative / follow-ups)
Clarifies private recovery under ADR-0008; source trust and sharing restrictions stay intact. Benefit: recoverability without accidental corpus export. Cost: password recovery is impossible; large archives require a reviewed bounded format. Alternatives: encrypted-volume storage only, or full corpus backup as default (rejected).

## Alternatives considered
See consequences above; retain the implemented fallback until each replacement passes acceptance checks.

## Evidence / sources
https://cryptography.io/en/stable/fernet/
Project: docs/IMPROVEMENT-PLAN.md; docs/HANDOFF.md; relevant slice docs and implementation.
