# Retry failed archive members

Resuming an import must retry temporarily failed members even when their archive traversal finished.
Use the latest outcome for each URI across the resume chain; reopen containers with retryable members and skip successful members.
Preserve original files, provenance, import settings and document versions. Permanent skips remain terminal.
No API, schema, UI, learning event, model routing or accessibility changes.

## Reproduction and verification

A two-member synthetic ZIP with one temporary I/O failure reproduced a resume that skipped the entire ZIP.
Regression covers successful-member preservation, repeated temporary failures, no duplicate versions and skipping the archive after recovery.
421 backend tests, full lint/types and independent code review pass with no blockers or majors. Existing running processes retain their loaded implementation; do not restart them merely to load this fix.
