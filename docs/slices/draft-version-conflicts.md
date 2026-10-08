# Draft version conflicts — R4 bounded slice

Story: a learner reviewing one draft must not overwrite or activate a different version saved elsewhere.
Inputs: draft identity, expected saved version and optional edited payload. Output: updated draft or explicit conflict; unsaved editor text remains.
Scope: serialize save/activate/discard using existing SQLite draft version; no migration, model call, learning evidence event, mode/energy change or automatic merge.
Accessibility: conflict feedback and an explicit keyboard-accessible latest-version read; keep current edits visible until the learner discards them.
Acceptance: stale and concurrent saves, stale activation/discard, ownership, terminal states, dirty-editor recovery, failed refresh, keyboard/narrow flow.
Baseline: /tmp/draft-conflict-before.log reproduces stale version1 replacing saved version2 with200/version3.

## Implemented — 2026-10-08
HTTP save, activation and discard now require the reviewed expected_version. A short SQLite write lock re-reads the owned row before comparison, validation and mutation. All three paths serialize; successful terminal actions advance the revision. A rejected draft cannot be activated. Internal callers may explicitly act on the latest locked draft without a client version. No migration, LLM, scoring, source rewrite or learning-state policy changed.

The shared area/course editor sends the displayed revision. On conflict it keeps local text, blocks saving/activation and offers Load latest saved version. Reads are bounded and failures keep both text and conflict. A successful read does not replace dirty text; the learner can copy edits before explicitly discarding them to adopt the saved version. Visual inspection found repeated notices, consolidated into one adjacent recovery panel. No automatic merge or retry was added.

## Verification
- Reproduced stale overwrite before implementation: /tmp/draft-conflict-before.log.
- Full backend: 937 passed (three existing warnings); full frontend: 541 passed. Logs: /tmp/draft-conflict-full-{backend,ui}.log. Targeted tests cover concurrent editors, activation/edit race, stale activation/discard, missing revision, foreign ownership, terminal states and failed latest reads. The final presentation-only adjustment then passed 14 affected UI tests again.
- Seven isolated browser journeys passed, including existing Home area activation. The two conflict journeys passed again after the final presentation adjustment at 390/1280px, with preserved text, explicit keyboard read/discard and no horizontal overflow. Screenshots inspected: /tmp/draft-conflict-{390,1280}.png. Browser responses simulate conflict; backend tests exercise real SQLite serialization.
- Ruff, full backend mypy (204 files), frontend lint/type checking and production build pass. Existing build chunk-size warning remains. Independent code and recovery-copy review found no blockers/majors; final visual adjustment changes placement/duplication only.
- Idle live backend gracefully restarted after confirming no running imports or established connections. Health200 and the required revision contract verified. No live draft was edited, activated or discarded by verification.

## Compatibility and remaining work
Old API clients must read the current version and include expected_version; missing versions fail422 rather than silently overwrite. Already saved draft payloads and versions need no migration. R4 is only partially covered: unsaved JSON remains page-local and can still be lost on reload; durable editor recovery, merge assistance, other learner-work envelopes and human usability acceptance remain open. Browser-keyboard evidence is not screen-reader certification. A database uniqueness constraint for learning-object versions remains a separate schema defense; this slice serializes the existing publishing path.

Next: version-bound recovery for unsaved editor text across reload, retaining conflicts and explicit discard without automatic publication.
