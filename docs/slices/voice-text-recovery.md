# Voice text recovery

Retain the latest transcript, received reply and unsent typed draft in this tab across navigation
or reload. Scope by session, skill, language and conversation mode. Restore disconnected, with
an explicit incomplete-text notice; no microphone, socket, playback buffers, saved-answer receipts
or learning evidence are restored. Stop preserves text; explicit Clear removes it. Mode/energy
remain learner-controlled. Storage errors are visible and do not erase the active text.

Implementation: bounded 250k-character JSON, 250ms batched writes plus pagehide/unmount flush.
Context changes remount and dispose the old voice loop. Clear failure keeps the panel open with
an actionable warning. Panels without an external close action expose Clear voice text.
No new database/API/model dependency, no raw audio retained. This is tab-local text recovery,
not live stream reattachment, durable voice submission identity or exactly-once inference.
Closing the tab or clearing browser storage can lose this recovery; completed saved answers
remain separate. Personal-recording gate stays open.

Acceptance: restoration without socket/microphone/playback, target isolation, explicit clear,
failed clear retaining current work, corrupt/oversized storage and write denial, pagehide flush,
component/browser checks, lint/build and required code/pedagogy reviews. Verification: full frontend258, lint/types and production build passed; two isolated desktop/narrow browser journeys verified reload, explicit keyboard clearing and zero voice sockets. Required code/pedagogy reviews found no blockers or majors; restoration wording was made past-tense so it stays accurate after manual reconnection. Synthetic tests only; no live microphone capture or model calls.
