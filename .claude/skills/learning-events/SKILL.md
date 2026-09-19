---
name: learning-events
description: How to emit and query learning events (xAPI-style) — the verb enum, envelope, and which events every feature must write. Claude loads this when implementing any service that touches learner state, reviews, tutoring turns, or preferences.
user-invocable: false
---
# Learning events

Envelope and verb list: `docs/EVENT-SCHEMA.md` (source of truth). Writer: `backend/app/db/events.py` → `events.emit(verb, object_type, object_id, *, session_id, result=None, context=None)`; it fills ts/ULID/mode/energy/experiment_arm from the session context automatically.

Mandatory events per feature:
| Feature | Verbs |
|---|---|
| Tutor turn (+ `tutor_trace`, `model_call` rows — traces are separate from events) | `asked`, `explained` (context: representation, hint_count, cited_sources, model, route) |
| Regenerate / choose explanation | `preferred` (result: chosen_id, rejected_id) |
| Assessment item | `attempted` (result: correctness, confidence_pre, latency_ms, hint_count), `graded` (result: score, criteria, misconception) |
| FSRS review | `reviewed` (result: rating, latency_ms, predicted_retrievability, days_since_learned) |
| Session | `started`, `block_started`, `block_ended` (context: block_type, planned_min, actual_min, switched_early, reason), `ended` (result: energy_after, self_report) |
| Adaptation | `adapted` (context: what, why, reversible), `undone` |
| Parking lot | `parked`, `promoted` |
| Voice | `spoke` (context: stt_ms, llm_first_token_ms, tts_first_audio_ms, total_ms) |
| Movement/language/guitar block | `practiced` (context: domain, activity, duration, self_rating) |
| Experiment | `assigned` (arm), `measured` |

Rules: append-only; result/context are JSON with only documented keys; add a new key → update EVENT-SCHEMA.md in the same commit. Query helpers in `db/event_queries.py` (e.g. `retention_by_representation()`, `events_for_session()`); add a helper rather than ad-hoc SQL in services.
