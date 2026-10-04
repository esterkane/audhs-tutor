# C6 save identity in the capture UI

Problem: the backend accepts durable request identities, but UI requests are still unkeyed. Persist an optional validated request key with the existing tab draft before submission, reuse it for unchanged retry/reload, clear it on editing, and never submit on restoration. Legacy/edited unconfirmed drafts explicitly warn that a new save cannot be matched to the previous request and label the action Save as new thought. Replay of promoted/dropped items reports actual status without restoring them.

Files: capture button, draft helper/tests, API wrapper and browser recovery tests. No learning-kernel change. Verify exact key/context replay after refresh, editing/legacy warnings, unavailable storage, no auto-submit and dropped replay.

Implemented and verified: 5 draft tests in both variants; final sanitized 14 browser journeys passed including unchanged retry after refresh, edited/new identity, legacy draft handling, keyboard, narrow/desktop and prior capture/actions. Lint/types passed both variants; original production build passed with existing chunk/worker warnings. Restored 390px draft screenshot inspected. Read-only recovery review found no blockers/majors. Storage failure preserves current in-memory identity but cannot guarantee it survives reload; warning retained. Source return and undo remain open.
