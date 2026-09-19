# Slice: events-traces (Stage 0)

**Story.** Every feature can record what happened (learning events) and why the system did it (traces) with one call each, and nothing can write an undocumented payload key.
**In/out.** `app/db/events.py`: closed `Verb` enum, `EventContext` (learner, session, mode, energy, socratic, arm, domain, activity, modality) stamped on every row, `EventWriter.emit()` validating result/context keys against `PAYLOAD_KEYS` (mirrors `docs/EVENT-SCHEMA.md`). `app/db/traces.py`: `write_model_call`, `write_retrieval_trace`, `write_tutor_trace` from Pydantic records; `hosted_spend_since()` for the budget. `app/db/event_queries.py`: `events_for_session`, `count_by_verb`, `last_event`. `app/schemas/common.py`: Mode/Domain/ActivityType/… enums.
**Events.** All of them; this slice is the writer. Adding a key = edit `PAYLOAD_KEYS` and EVENT-SCHEMA.md in the same commit (test enforces every verb has rules).
**Mode/energy.** Read from `EventContext`, never guessed.
**Verified by.** `tests/test_events_traces.py`.
