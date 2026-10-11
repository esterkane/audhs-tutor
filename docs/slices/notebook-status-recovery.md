# Notebook setup status recovery

2026-10-11. Reproduced a stalled status GET: after15 seconds no failure or Retry was visible. Reused boundedRead for a15-second complete-response deadline, added visible pending status, disabled automatic query retries, and stop background polling after a failed read. Explicit Retry only reads status; successful active-setup responses restore polling. No POST behavior, installation, cell execution, model routing or learning state changed.

Before/after unit reproduction fails before the change and passes after it. Three focused UI tests cover setup, stalled-read retry without any POST and stopped error polling. Three isolated browser journeys pass: existing prepare/open flow plus390/1280px stalled-read recovery by keyboard, with no start requests and no horizontal overflow. Narrow recovery screenshot inspected. Focused ESLint, types/production build and independent review pass; existing build chunk-size warning remains.

Remaining: start/install POST interruption and server-job failure recovery need their own mutation-aware contract. This read-only timeout must not be used as proof that setup stopped or as permission for an automatic restart. Human comprehension and physical audio acceptance remain open.
