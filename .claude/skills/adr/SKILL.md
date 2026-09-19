---
name: adr
description: Write an Architecture Decision Record in docs/adr using the project template; supersede rather than edit accepted ADRs. Use when a binding decision is made, changed or challenged.
argument-hint: "[title]"
disable-model-invocation: true
---
# New ADR: $ARGUMENTS

Existing ADRs: !`ls "${CLAUDE_PROJECT_DIR}/docs/adr" 2>/dev/null || echo none`

1. Next number = highest existing + 1 (4 digits). File `docs/adr/NNNN-<kebab-title>.md`.
2. Template:
```
# NNNN — <title>
Date: <YYYY-MM-DD>
Status: Proposed | Accepted | Superseded by NNNN
## Context
## Decision
## Consequences (positive / negative / follow-ups)
## Alternatives considered
## Evidence / sources
```
3. If this changes a "Binding decisions" bullet in CLAUDE.md, update that bullet and link the ADR. If it supersedes an ADR, set the old one's Status line (the only edit allowed on an accepted ADR).
4. Status stays `Proposed` until the owner says accept; then flip to `Accepted` in a separate commit.
