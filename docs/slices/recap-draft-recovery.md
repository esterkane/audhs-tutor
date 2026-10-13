# Recap draft recovery

Completed 2026-10-13. Real sandbox journeys reproduced recap notes disappearing after reload at390/1280. Notes and optional ratings now recover from a versioned session-specific browser-tab draft. Malformed earlier storage is retained without overwriting; read/write failures warn the learner. Successful explicit save clears a readable draft; failed saves retain it. Fields pause during saving, duplicate clicks are guarded, and late completion cannot reset a different or unmounted session. No automatic submission or learning policy change.

Evidence: four hook tests cover restoration/session isolation/clear, failed writes, malformed history and failed removal. Two real sandbox browser journeys cover reload, keyboard editing, responsive overflow, held-save disabled input and successful cleanup. Both screenshots inspected. Targeted lint and production type/build pass; code and pedagogy reviews resolved two majors and found no remaining blockers/majors.

Limits: recovery lasts for this browser tab, not across devices or closed tabs. No human screen-reader acceptance. Unreadable drafts remain stored even after saving new notes. Broader end-session recovery and integrated acceptance remain open.
