# C6 original context and C7 recent destination contract

## Evidence before implementation

Saved thoughts currently retain session_id/node_id but show no source label or return action. Promotion can replace node_id. Consequently node_id cannot serve as immutable original context. The companion separately stores a raw path and page title; this does not validate resource identity or restore an old session. A generic href field would reproduce that gap in durable storage.

Inspected implementations: ParkingLotButton, parking API/ORM, LearningCompanion, Programs, Playground, Areas and ProjectAudioContext. Programs resolves course/step/view from URL and checks stale locations against its local manifest. Playground resolves workspace or a lesson session/skill pair; linked lesson context is checked against current server activity. Areas supports area/draft identity. Project audio context validates the current manifest relationship. None of these establishes portable media position or several independently resumable sessions.

## Shared typed representation

Use a versioned, bounded original-context value, not arbitrary URLs or copied page text. Its kind owns its identity fields. Derive navigation from those fields using an allowlisted resolver. Store a short display label as a historical label, never proof that the target still exists. Do not include credentials, external links, file-system paths, DOM text or model output.

| Kind | Identity | Return semantics |
| --- | --- | --- |
| lesson | session ID, skill ID, block identity when present | Check authoritative current session. Resume only a matching checkpoint. Otherwise show original lesson selection with explicit Keep/End-and-start choices; never resurrect a historical session. |
| area | area ID | Browse the exact area, without changing active learning target. Missing area offers Browse areas. |
| project step | course ID, section ID, view=guide/notebook | Resolve against the local manifest; open exact step/view. Existing notebook content-hash recovery still governs source edits. Never claim temporary execution outputs restored. |
| coding workspace | known activity ID, optional lesson context | Reuse existing workspace query/deep-link validation and saved-code boundary. Unknown activity gets explicit recovery, not silent Scratch substitution presented as success. |
| audio lab | known lesson/preset identity where available, optional validated project relationship | Open relevant lab context; no autoplay or promise of local file/position restoration. Unsupported identity offers Open audio lab with that limitation. |
| saved explanation | answer ID | Open exact existing detail, preserving provenance; missing/deleted answer exposes library recovery. |
| source | stable chunk/document identity | Use source viewer/read-only source detail after identity validation. Do not manufacture a public URL or open private paths from stored text. |

Pages without a reliable item identity can capture a thought without a return target. Explicitly say that no exact place was attached. Do not infer the current lesson from the browser's stale persisted session ID while the learner is in another workspace.

## Execution sequence

1. Add a small shared frontend context classifier/resolver and tests for supported routes/identities. Read current resolved screen state where URL is insufficient. Capture context on first nonempty draft edit, alongside original session/skill. It must remain unchanged while browsing or retrying.
2. Add optional bounded context schema to POST/GET parking and a nullable original_context_json column. Include immutable context in the request fingerprint. Legacy rows stay contextless: never backfill a guessed original place from mutable promoted node_id. Regenerate API types with sanitized deltas only.
3. Render historical context label and an explicit Open original material action in saved thought lists. Resolve before navigating. Close capture dialog and restore meaningful destination focus. Loading/error/stale states need their own feedback and retry; navigation performs no learning mutation.
4. Reuse the same typed identity for C7 recent destinations. A visit is not mastery or completion. Keep browsing history separate from active-session checkpoints. Inventory real search stores before a command palette claims global search.

Do not make the tutor context silently follow navigation. Integrating its raw path checkpoint with this typed representation is a separately verified compatibility change; existing captured text and conversations must survive.

## Acceptance matrix

- Save from a guide/notebook, switch topics, reload, reopen exact original material; preserve saved code and notes.
- Save during an active lesson, then end/start another: return must explain the mismatch and never silently resume or replace the new session.
- Capture draft in one context, navigate before submission, then retry: original identity and request payload remain identical.
- Promote to another node: original context remains unchanged.
- Deleted area/source/answer, changed manifest or notebook hash: explicit recovery and no fabricated restoration.
- Unsupported/malformed context and external-path injection rejected; existing legacy thoughts remain readable.
- Keyboard link activation/dialog close, desktop/narrow layouts and focus restoration; no hidden mutation or autoplay.
- Storage failures and migration preserve active drafts and old records. Test exact source identity, not just destination pathname.

## Boundary

This is the required architecture contract before schema/UI expansion, not a claim that source return is implemented. C6 reversible action semantics remain separate. C7 typed recents/search remain incomplete. No new dependency, paid service or learning-kernel policy is proposed.

Baseline evidence: 12 isolated browser journeys passed for area history, coding-workspace history/reload, lesson/code return, authored audio context (including missing/changed relationships) and notebook-start timeout recovery at narrow/desktop sizes. These validate existing route building blocks, not the unimplemented durable capture links. No runtime change in this contract slice.

## First durable return slice — 2026-10-04
Implemented optional typed context for area, project step/notebook, saved explanation and standalone coding workspace. Context is captured on first draft edit and retained across navigation/reload/retry; stored separately from mutable node_id and included in keyed-save fingerprints. Migration d056ab1248ce leaves legacy contexts null; previous keyed saves retain compatible fingerprints when no context exists. Lists expose Open original material, closing the capture dialog. Destination screens retain their stale/deleted recovery. Unsupported contexts explicitly have no exact link.

Review caught requested URL versus displayed identity during dirty area history navigation. Resolved screen markers now govern area/project/workspace capture; stale project locations suppress capture. Regression covers dirty area A while history requests B. No learning decisions changed.

Evidence: 14 backend tests in both checkouts including migration preservation, context promotion/replay and old-key compatibility; 8 frontend unit tests in both. Original 16 capture/action browser journeys passed, then final sanitized 6 journeys cover dirty area/history, exact saved workspace return and lesson-playground regression at 390/1280. Keyboard link activation and modal close verified; returned narrow workspace screenshot inspected. Ruff/mypy, frontend lint/types/build passed; inherited build warnings remain. Code/recovery review clear after fix. Project notebook context is covered by typed resolver/storage checks, not a new end-to-end notebook return test in this slice.

Remaining: authoritative lesson checkpoint return, audio-lab identities, source-viewer capture, project-notebook saved-thought end-to-end acceptance, malformed/stale target expansion, source labels more specific than page headings, reversible thought actions and C7. Do not mark all original-context requirements complete.

## Task notebook round-trip correction — 2026-10-04
A new end-to-end journey reproduced a real gap: closing a task starter after saving a thought caused the original link to reopen only the guide. Added distinct project view=task (separate from the full course notebook). The displayed task marks its exact context; capture chooses the innermost active marker. Returning opens the starter without executing code, and Back to task removes the explicit task query. Missing project steps suppress nested capture markers; missing task notebooks show recovery text. Existing source/hash checks still govern notebook work.

Final sanitized verification: 5 browser journeys passed, including saved-thought round trips at390/1280, retained edited code and notes, keyboard link activation, missing-step capture suppression, timeout recovery and local run-all/check/results return. Narrow returned notebook inspected visually. 9 frontend unit and5 backend tests passed; lint/types/build passed (inherited warnings unchanged). Review found no major issue; its stale-marker observation was fixed and tested. No assessment/learning policy changed. Full course notebook and other context types retain their existing scope; session/audio/source return and undo remain open.

## Displayed lesson return — 2026-10-04
Session-screen capture now records authoritative displayed skill, session, block index and block start identity, with the actual lesson title. OriginalLesson performs a fresh read on explicit return. It resumes only the same running checkpoint; moved/ended sessions offer the existing selected-lesson choices without any learning write. Failed reads retain the thought and offer retry; closing aborts/ignores late navigation. Review and recap screens without an exact displayed skill still do not manufacture lesson identities.

Verification: 11 sanitized browser journeys passed (lesson return plus pause/late-response regressions), followed by both final390/1280 lesson journeys after improving the captured title. Checks assert no session writes during return or fallback. Six frontend and5backend tests passed; lint/types, targeted Ruff/mypy and original build passed with existing warnings. Narrow mismatch state inspected. Read-only review found no blockers/majors. Audio/source capture, reversible actions, richer labels elsewhere and C7 remain incomplete.
