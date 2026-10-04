# C7 recent contexts and search

## Inspected starting point — 2026-10-04
Home RecentAreas reads a tab-local five-ID area history and resolves current titles through the area API. It is browsing history, separate from active session and goal settings. There is no general recent-context list. Keep its area validation/recovery until a replacement offers the same functionality.

The capture context union now supports area, project step/guide/task/full notebook, source chunk, saved answer, standalone workspace, built-in audio lesson and exact lesson checkpoint. Reuse that identity contract. A raw URL, underlying page marker or stale stored session ID is not evidence of the currently displayed item.

## Foundation implemented
features/recent/history.ts provides a versioned tab-local store, bounded to12 deduplicated identities. It copies only the approved context fields, refreshes labels on later visits and never stores raw source text, arbitrary URLs, playback or progress. Corrupt/oversized storage is rejected with a status; write failure retains in-memory entries; Clear reports failure if old data may return. It does not yet record visits or change a screen.

Four unit checks pass: bounds/deduplication/label refresh and reload, invalid identity/corrupt storage, incidental-field removal, failed storage writes and failed/successful Clear. Lint/types pass. Integration must disclose that this is this-tab navigation history, not saved learning work or cross-device resume.

## Next bounded UI integration
Use explicit resolved view identities, not a document-order observer. Record each destination after successful resolution; do not record errors, pending URLs or incidental prefetches. Start with existing source/workspace views and then include project/answer/area/audio/lesson with their respective validated return contracts. Preserve query/checkpoint/code state separately. No new session starts or autoplay. Lesson return must use OriginalLesson's fresh checkpoint check rather than a plain /session link.

Expose a compact Home disclosure of recent material below authoritative Resume, with type/label and Clear history. Preserve existing recent-area behavior until verified within the unified presentation. Returning uses existing stale/deleted recovery. Add a storage-error notice that explicitly says an old history can reappear after failed clearing. Avoid creating another floating control or forcing a new startup decision.

Required journeys: visit material A/B, Home, keyboard return to A, reload, stale/deleted target, pending navigation, failed storage and clear, desktop/narrow reflow; assert no learning writes. Existing recent-area and session-resume journeys remain regressions. No mastery indicators derived from visits.

## Search inventory: verified first stores
| Store | Existing operation | Constraints |
|---|---|---|
| Completed saved tutor answers | GET /api/answers with q and filters; SQLite tutor_answer_fts | Learner-scoped, paginated; literal query preparation; not all conversations/drafts. |
| Indexed source passages | POST /api/corpus/search | Retrieval repository/embedding readiness; source provenance and quarantine semantics retained; Library currently requests8 hits. Independent failure from answer search. |
| Knowledge areas | GET /api/areas | Catalog available; not a verified full-text search endpoint. |
| Recent destinations | New bounded browser-tab store | Navigation identities/labels only; not a corpus index or evidence. |

Project manifests, skill catalog, notebooks/learner-authored work and other stores still require explicit inventory before claiming global coverage. Do not create a duplicate search database or silently submit corpus text to hosted inference. A future federated search must show result kinds, provenance, independent loading/error states and exact return destinations; a source match is not fact verification. Command-menu keyboard/focus design follows this inventory rather than preceding it.

C7 remains incomplete; no new recent-material UI or global search is claimed by the foundation.

Baseline browser evidence: three Home recent-area journeys pass, including390/1280 keyboard return without learning writes and catalog failure recovery. The new store has four passing unit checks in both checkouts. Read-only review found no blockers/majors. No rendered surface changed in this increment.


## First displayed destinations — 2026-10-04
Home now has an optional Recently opened material disclosure below the primary learning action. Resolved matching source chunks and known standalone coding workspaces record typed visits. Failed/pending source lookups, unknown-workspace fallbacks and linked lesson experiments are not misrepresented as successful standalone visits. Existing recent areas remain intact. Links reuse established return/error routes; Clear removes only this material history, never saved work or learning progress.

Original6browser journeys passed: recent sources/workspaces390/1280, keyboard return, reload, deleted-source recovery, clear, unknown workspace suppression and existing recent-area regressions. Seven unit checks, lint/types and production build passed (inherited build warnings remain). Narrow screenshot inspected; read-only review found no blockers/majors. No learning writes in the browser journeys. Next: resolved project/answer/audio/lesson destinations, area-history reconciliation and remaining search-store inventory. Human acceptance and global search remain incomplete.

Final sanitized verification:3recent-material browser journeys and lint/types passed.


## Saved explanations and audio lessons — 2026-10-04
Matching loaded saved answers and the displayed audio Learn step now join recent material. Answer history is not recorded during loading/error; audio links retain the explicit Open saved audio lesson action and never start playback. Visual inspection shortened redundant audio labels. Original six browser journeys passed (new recent-answer/audio390/1280 plus saved-answer and saved-audio regressions), with no learning writes or AudioContext creation. Lint/types and production build passed with inherited warnings; read-only review clear. Project/checkpoint tracking, area consolidation and remaining search inventory still follow.

Final sanitized rerun: both390/1280 journeys passed after the label change. The preceding run was already in progress when the label changed and retained the old locator, causing its desktop case to time out; rerun used the final code and selectors.


## Project views and lesson checkpoints — 2026-10-04
Resolved displayed guide/task/full-notebook project destinations now record distinct history identities; hidden, paused and stale-location branches do not record visits. Full notebooks require a resolved section because the existing return contract is section-scoped. Running lessons record session/skill/block/start only when the matching active skill is present and the session query has not failed. Returns use OriginalLesson's fresh server read, never a blind session URL or learning mutation. Display labels are capped to the shared200-character contract.

Four browser journeys pass in both checkouts at390/1280: task return retains edited code and notes, missing project-step URLs are not recorded, matching lesson return resumes, moved/ended session offers explicit choices without session writes. Lint/types/build pass (existing build warnings); title bounding was followed by type checking. Narrow lesson-recovery screenshot inspected; read-only review clear. Full-course notebook recent-link coverage and human acceptance remain open. Review/recap without exact displayed identity remain excluded. Next: area-history reconciliation and remaining searchable-store inventory; do not call all C7 done.


## Area presentation and remaining store inventory — 2026-10-04
Home now groups RecentAreas inside the existing recent-material disclosure, preserving its catalog validation, missing-area message, retry and Browse all areas. The shell area picker keeps its own current/recent IDs; material-history clearing explicitly does not reset that browsing context or saved work. This intentionally shares presentation rather than maintaining two competing area-selection stores.

Additional verified stores for search planning:
- Skill catalog: GET /api/skills and /api/skills/map provide typed IDs/titles/descriptions and server-computed learner state, not a query endpoint. A bounded client title filter may offer read-only map/lesson-choice destinations; searching cannot select a goal or start a session.
- Project guide: Programs reads /local-learning/program.json through parseProgram. It contains course/section titles and authored guide text plus local notebook references. Search can inspect this validated manifest with course+section identity; absent/private manifests must be an independent unavailable category, never a fatal whole-search error.
- Notebook files and edited work: NotebookReader loads individual local notebook files; NotebookWorkspace keeps hash-scoped edits in localStorage. GuidedSection uses project-study:v1:<course>:<section> for learner notes. These have no verified aggregate full-text index or query API. Do not scan all browser storage or claim notebook/code/notes search. Offer their existing project destinations until an explicit privacy/versioning/index contract exists.
- Saved thoughts: GET /api/parking filters only by status and is learner-owned. No query or pagination contract exists. Do not silently load every removed thought into a global search index. A future bounded search endpoint can be a separate slice.
- Completed saved answers and source retrieval remain the two existing query services described above. They have different ranking, availability and trust semantics; do not combine scores into a fabricated relevance scale.

Next bounded search UI: an explicit Search material entry and page that independently queries saved answers and indexed sources on submit, with separate status/retry and result categories. Query in URL supports Back/refresh. A failed retrieval service must not hide available answers; source search is not web search or fact verification. Preserve exact answer and chunk return links. Explain exclusions (notebook edits, unsaved chats and notes), provide existing catalog/project navigation, and retain recent history separately. Keyboard command-menu access can follow this proven page; no new model, hosted service or duplicate database. Whole-platform search coverage is not claimed.

Area consolidation verification:6original browser journeys passed (area and material history), lint/types/build passed with inherited warnings; narrow layout inspected and read-only review clear. Initial area tests incorrectly toggled an already-restored open disclosure closed after Back; corrected to inspect open state before activating. No learning writes or area-selection resets.

Final sanitized3area-history journeys and type check passed.
