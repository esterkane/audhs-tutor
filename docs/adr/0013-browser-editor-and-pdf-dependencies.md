# 0013 — Browser testing, code editor, PDF import and offline Python runtime
Date: 2026-09-21
Status: Proposed

## Context
Owner requested resolution of the dependency decisions in IMPROVEMENT-PLAN and execution of the local setup and commit plan.

## Decision
Approve @playwright/test as a development dependency for isolated application browser journeys. Approve @codemirror/lang-python and @codemirror/commands to complete the declared editor stack; retain accessible keyboard escape and textarea fallback. Prefer a pinned, locally served Pyodide runtime plus NumPy and lock metadata, downloaded by an explicit reproducible setup script; never commit large runtime artifacts or silently fall back to a CDN. Until vendoring is implemented/tested, document the current pinned CDN behavior. Defer pypdfium2: first use existing pypdf for text-PDF glossary preview; add a second parser only for a demonstrated rendering/extraction requirement.

## Consequences (positive / negative / follow-ups)
Benefit: reproducible browser coverage and local-first code exercises. Costs: browser/runtime disk space and setup step. Dependency approval does not imply the associated UI, PDF import, or offline runtime is already implemented. Alternatives: keep textarea/API-only tests/CDN indefinitely, or add PDFium without a concrete requirement.

## Alternatives considered
See consequences above; retain the implemented fallback until each replacement passes acceptance checks.

## Evidence / sources
https://pyodide.org/en/stable/usage/downloading-and-deploying.html
Project: docs/IMPROVEMENT-PLAN.md; docs/HANDOFF.md; relevant slice docs and implementation.
