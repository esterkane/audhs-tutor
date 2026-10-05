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


## Material search page — 2026-10-04
Library now offers Search material. Explicit submission searches saved explanations and indexed source passages independently, using the existing bounded read APIs. Query lives in the URL for refresh/Back; exact answer/chunk links preserve identity. Each category has independent loading, empty and retry states. Historical answers are not presented as reverified; source warnings and quarantine remain visible. Exclusions are explicit: notebook edits, unsaved chats, project notes and saved thoughts are not searched. No new backend, dependency, hosted model or learning-state write.

Original verification: three browser journeys pass at390/1280, covering keyboard submission/opening, independent source retry, Back/reload/clear, invalid query and stale-answer completion. Narrow screenshot inspected; lint, types and production build pass with inherited bundle/worker warnings. Initial passing run exposed duplicate sibling React keys; prefixed keys fixed and all three journeys rerun cleanly. Read-only code/UX review found no blockers or majors.

Still open: global shell search/command access, additional searchable categories with verified contracts, broader accessibility/theme/zoom checks and human comprehension acceptance. This is the first two-provider search page, not completion of C7 or the whole design system.

Final sanitized verification: all3 material-search browser journeys and type check passed.


## Persistent search access — 2026-10-04
Header now exposes Search material without requiring Library discovery. Native link preserves standard navigation and existing main-content focus; no search request until a query is submitted, and no learning mutations. Five original browser journeys pass, including390/1280 keyboard tab access, Enter, Back, no writes and overflow checks; lint/types/build pass with inherited warnings. Narrow screenshot inspected; review found no blockers/majors. Mobile header remains tall: consolidate chrome in a separately evaluated slice, preserving reachable audio Stop and contextual tutor. Command palette and wider search categories remain incomplete.

Two initial browser attempts timed out before tests. A Python faulthandler trace identified LiteLLM import waiting on remote model-cost-map HTTP fetch. Verification used LITELLM_LOCAL_MODEL_COST_MAP=True (supported by installed dependency) only for hosted-disabled sandbox. Separate architecture follow-up: remove unneeded network dependency from local startup while preserving current hosted cost accounting; no production pricing behavior changed here.

Final sanitized verification: all5 search journeys passed with the same sandbox-only local-cost-map setting.


2026-10-05 header spacing: brand and search share a wrapping row on narrow screens. Screenshot shows header reduced from276px to243px at390 width; no controls hidden or learning logic changed. Five original search/keyboard/Back journeys, lint and types passed. Narrow screenshot inspected. Broader mobile composition and command access remain open.

Sanitized header keyboard/return journeys also pass at390/1280.


## Quick navigation — 2026-10-05
Header Search or go to opens a native modal over the current workspace; Ctrl/Cmd+K opens it outside text editors and other modals. Filtering page names is local; explicit submission navigates to material search. Existing Library search remains available. Close/Escape restores prior focus without navigating or discarding the underlying draft. Destination links reuse existing shell routes; no new backend, model call or learning-state write. Initial cancellation test exposed native search-input Escape consumption; explicit dialog Escape handling fixes it.

Seven browser journeys pass in both checkouts at390/1280, including preserved draft, shortcut editor guard, focus return, empty page-filter results, explicit search, Back and existing source retry/stale-query regressions. Narrow screenshot inspected; lint/types pass; build passed before the Escape event fix, with inherited warnings. Read-only review found no blockers/majors. Sandbox uses bundled LiteLLM cost map as documented above. Remaining: fuller modal/zoom/theme accessibility acceptance, additional material categories and human usability validation; C7 is not wholly complete.


2026-10-05 C7 area search: Search now reuses the bounded shared area catalog to match names, descriptions and topic terms by case-insensitive phrase. Separate result group, count/8-result cap, retry and exact browse links; opening an area does not start/change a session. Eight browser journeys pass in both checkouts, including unavailable retrieval alongside area results and zero learning writes; lint/types pass, narrow screenshot inspected, read-only review clear. Used separate sandbox ports8011/5175 and search-area-check.db. Project/skill/notes search and broader accessibility/human acceptance remain open.


2026-10-05 C7 project-guide search: separate validated/bounded manifest query searches course/section titles and explanations; exact course+step guide links, cap8 and total count.404 reports no guide; invalid/unavailable data gets independent retry. No notebook cells/notes indexing or code execution. Original9 and sanitized9 journeys pass; final sanitized rerun uses explicit404 default fixture so unrelated tests cannot read owner material. Lint/types pass, narrow layout inspected, read-only review clear. Skill/notes search and broader acceptance remain incomplete.


2026-10-05 skill search: read-only catalog title/description matching, capped results, prerequisite status without fabricated mastery, exact existing lesson-choice links. Ten browser journeys pass in both variants, including no learning writes from result navigation; lint/types pass, narrow screenshot inspected, read-only review clear. CURRENT-WORK now begins with a reconciled execution checklist superseding historical next-step paragraphs. Search category orientation and broader daily-learning acceptance are next; notes/notebook search remains excluded.
