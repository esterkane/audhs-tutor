# Saved-answer lifecycle: QA00 inventory

Inspected 2026-10-01 against e162e4c. This is design evidence, not an implemented answer store. The saved-answer queue remains open.

## Actual response paths

| Path | Producer / delivery | Existing retained state | Persistence integration |
|---|---|---|---|
| Lesson explanation, assessment hint, language chat | `orchestrator/tutor.py:TutorTurn.run`; `/api/tutor/stream` and buffered `/api/tutor/turn` | TutorTrace stores metadata, checkpoint stores turn/action context, not complete response text | One shared producer finalization; do not save separately in both HTTP routes. Record final `TurnDone.text`, which can differ from streamed tokens after tail trimming. |
| Live voice conversation | `voice/loop.py:_respond` consumes the same `TutorTurn.run` | Trace/events and optional retained recording; no separate answer library | Reuse tutor record. Track text completion separately from speech completion/interruption. A synthesized response does not prove it was heard. |
| Notebook step chat, Socratic follow-up, answer feedback | `features/programs/StudyTutor.tsx` → `/api/playground/tutor` → `orchestrator/playground.py:respond` | Bounded browser history and workspace snapshot; trace contains metadata only | Save exact returned text plus bounded request snapshot. Add structured course/area/step identity: current request has only session, exercise text, code, output, history, intent and question. UI `identity`/targetLabel are not sent as stable backend scope. |
| Standalone playground | Same playground endpoint | Frontend conversation/execution state, model trace | Same persistence service; label advice for exact code/output hash. It is not a general course FAQ. |
| Alternative representations | `orchestrator/representations.py:render` and `/api/objects/{skill_id}/representations/{kind}` | Representation content and model-call ID already in database; cached path now preserves generation-time source metadata | Implemented in representation-answer-history: snapshot delivered text and its ID/version when available. `kernel/representations.py:invalidate` deletes cache rows, so a bare foreign key cannot preserve history. No model call on reopen/cache hit. Capture sources at generation; missing historical citations remain unknown. |
| Assessed-answer feedback | `orchestrator/grader.py`, assessment API | AssessmentAttempt stores learner answer and deterministic/LLM result JSON with feedback | Reference existing attempt; do not rerun grading or duplicate evidence. Personal feedback excluded from default general suggestions. Distinguish it from StudyTutor's conversational feedback. |
| Read aloud / dictation / notebook execution | Existing voice reader, dictation, notebook service | Audio/model/runtime events or outputs | Not new answers. Reading or dictating does not create another Q&A; executing a notebook does not certify the tutor's advice. |

## Transaction evidence and risks

`db/session.py:get_db` yields a session but does not commit it on exit. `db/traces.py` writers and `db/events.py:EventWriter.emit` commit by default; the tutor finalizer invokes these and checkpoint writes before yielding done. A proposed answer insert must have an explicit transaction owner, not rely on dependency teardown. Avoid leaving pending answer mutations before helpers that implicitly commit.

Playground checks session learner ownership explicitly. At the QA00 baseline, tutor HTTP and representation routes derived the learner from a supplied session; The tutor-session-ownership prerequisite now adds current-owner checks (the local app uses a get-or-create-owner dependency, not a multi-user login system) at the exposed boundary before persistence/replay, with cross-learner denial tests (see docs/slices/tutor-session-ownership.md). Never take learner_id from the client. Voice session validation needs its own test, not an assumption based on HTTP checks.

`TutorTurn.run` finalization also runs on interruption. Do not equate reaching finally or writing a trace with completed output. A gateway partial result produces outcome=partial; cancellation may never deliver done. Only completed, nonempty output is eligible for suggestions. Keep raw received prefix distinct from the final canonical text.

Generation completion, HTTP/SSE receipt and successful audio playback are separate facts. The server cannot prove receipt from writing a socket. Use generated-complete plus optional client acknowledgement; do not call this proof of reading, listening or mastery.

## Identity and scope

Add an explicit bounded context envelope: surface, parent_answer_id, real learner question, action/display label, stable material namespace/course/area/section/step IDs where available, skill/learning-object/assessment IDs, and material/code/output version fingerprints. Validate references and ownership. Unknown scope stays unknown; never infer a course by parsing the question or current global preference.

The selected action prompt is currently substituted into StudyTutor.question. Preserve the actual typed question separately from that internal prompt. Deterministically label action-only requests from their target, e.g. Explain selected step; do not invent learner wording. A course name is a label, not identity. Keep many-to-many area/source associations so cross-course learning remains possible.

Snapshot only bounded material actually supplied, not full notebooks, environment variables or complete model system prompts. Store source IDs, document version/hash, citation and cited/flagged status. Corpus passage bodies remain in the corpus; learner backup must not silently embed full corpus text through a new answer/context field. Answer text can itself quote material; document that limitation and apply existing private backup policy.

## Required next implementation tests

1. Full generated reply survives process/browser restart and is byte-for-byte the final response text. Stream prefix versus final trimmed text covered.
2. Duplicate save/replay, simultaneous requests and lost response after commit produce one entry; same intent key with different payload conflicts.
3. Interrupted/failed/empty replies never enter completed suggestions; Stop and late responses keep correct context.
4. Failed database save preserves delivered text with explicit unsaved state; retry does not regenerate or invent a model answer. A client recovery copy is unverified until reconciled with server identity/content.
5. Ownership checks cover tutor, playground, representations, voice and library endpoints. Search filters cannot leak another learner's rows.
6. Representation and assessment references reopen existing artifacts without model/grader invocation or additional learning evidence.
7. Learner export/wipe discovers the new LearnerScoped table; backup excludes corpus-only snapshots and FTS data follows deletion/restore. Full/private and learner-only restores tested on disposable databases.
8. Source/code changes flag stale context; report/hide actions reuse ContentReport.turn_id where applicable. Model output is never indexed as independent corpus evidence.

QA01 should first deliver complete tutor + playground persistence with explicit surface coverage, then representations/attempt links and voice verification before declaring QA01 complete. QA02/03 follow only when durable retrieval and ownership tests pass.

## Review and remaining implementation decisions

Independent code/architecture and pedagogy review found no blockers or majors in this design. QA01 must specify durable in-flight ownership and crash recovery: elapsed time alone must not start another generation while an old request might still run. On confirmed abandoned work, show interrupted/unknown completion and allow an explicit new attempt; never fabricate a completed answer. Define atomic claim/replay semantics and test process restart/concurrent workers.

After learner-only restore, retain answer text and source metadata but mark unresolved corpus references unavailable. A matching filename or title is insufficient to clear staleness; require original stable identity/version/hash or explicit reviewed remapping. FTS rebuilding must not make an unresolved record appear verified.
