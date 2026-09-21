# Learning-event schema (xAPI-inspired, local)

Table `learning_event` — append-only. One row per learner-relevant interaction. This is the raw material for the n-of-1 experiments, the open learner model, the phase-2 bandit and any later SFT/ORPO dataset.

## Envelope
| Column | Type | Notes |
|---|---|---|
| id | TEXT (ULID) | PK |
| ts | TEXT | UTC ISO-8601 |
| session_id | TEXT | FK session |
| actor | TEXT | `learner` \| `system` \| `tutor` |
| verb | TEXT | closed enum below |
| object_type | TEXT | `item` \| `node` \| `turn` \| `block` \| `session` \| `explanation` \| `adaptation` \| `note` \| `experiment` \| `model` |
| object_id | TEXT | |
| domain | TEXT | `ai_ml` \| `programming` \| `language` \| `guitar` \| `movement` \| `meta` |
| activity_type | TEXT | `new_material` \| `retrieval` \| `interleaved_review` \| `challenge` \| `domain_switch` \| `movement` \| `recap` \| `chat` |
| representation | TEXT NULL | `analogy` \| `derivation` \| `code` \| `diagram` \| `worked_example` \| `problem_first` \| `narrative` |
| modality | TEXT | `text` \| `voice` |
| mode | TEXT | `novelty` \| `steady` \| `low_capacity` |
| energy | INTEGER | 1–5 at session start |
| socratic | INTEGER | 0/1 session flag |
| experiment_arm | TEXT NULL | |
| result_json | TEXT NULL | verb-specific, keys below |
| context_json | TEXT NULL | verb-specific, keys below |

## Verbs and payload keys
| verb | result_json | context_json |
|---|---|---|
| started / ended (session) | `energy_after, self_report(1–5), notes?` | `planned_blocks` |
| block_started / block_ended | `actual_min` (server-measured from `block_started_at` when the client sends none), `switched_early`, `reason ∈ finished | switch_early | skipped | save_and_stop | session_end`, `timer_extension_min` (minutes the learner added via the soft timer) | `block_type, planned_min, node_ids` — object id `<session_id>:<index>`; exactly one start and one end per block (transitions are idempotent, `kernel/blocks.py`) |
| asked | — | `text_len, node_id` |
| explained | `sentences, cited_sources[]` | `representation (incl. `code_hint` / `full_solution` for item-scoped exercise help, P8), hint_count, model, route, prompt_version, latency_ms, tokens_in, tokens_out, cached_tokens, node_id, questioning_style (explicit \| socratic as requested), arm_intended? (experiment arm config for this turn), arm_delivered? (bool, only when the stream completed: a Socratic arm = the last sentence asks a question and the turn has ≤ 6 sentences, trailing `[n]` ignored; a representation arm = the detected representation equals the requested one; an explicit arm is delivered unless the mastery gate refused it — an explicit turn may end with a check question), arm_not_applied? (the mastery gate refused the arm's representation; P2 arm fidelity), usage_source (reported \| estimated \| unavailable — where the token counts came from; P6), cost_status (free \| reported \| estimated \| unknown; P6)` |
| preferred | `chosen_id, rejected_id, reason?` | `representation_chosen, representation_rejected` |
| attempted | `correct(bool\|null), confidence_pre(1–5), latency_ms, hint_count, answer_len` | `item_type, node_id` — since P7 the grader stamps `domain` from the skill node (language items → `language`, programming → `programming`; unknown → `ai_ml`) |
| graded | `criterion_results[{criterion,passed}], score(0–1 derived), misconception?, confidence, feedback_len` | `grader_level ∈ deterministic|deterministic:client-pyodide (P8 code exercise: checks ran in the learner's browser sandbox)|rubric|local|hosted, prompt_version, rubric_version` |
| evidenced | `skill_id, dimension, score, weight` | `attempt_id` |
| proposed (adaptation) / decided | `decision ∈ try|default|no|never` | `what, why, origin ∈ observed_pattern|planner` |
| reviewed | `rating(1–4), latency_ms, predicted_retrievability, days_since_learned (days since the previous review, or since the card was created; ≥ 0), stability_before, stability_after, confidence_pre?(1–5)` | `item_type, node_id` |
| adapted / undone | — | `what, why, reversible, policy_version` |
| parked / promoted | — | `node_id, promoted_to?` |
| spoke | `stt_ms, llm_first_token_ms, tts_first_audio_ms, total_ms, interrupted` | `first_chunk` (`clause`/`sentence`/null — what the first TTS request carried, so the early-speech gain is checkable in real sessions), `stt_model, tts_model, lang` — one per voice turn (P9); `domain=language` for conversation practice |
| practiced | `duration_min, self_rating(1–5)` | `domain, activity, notes?` |
| listened | `replays, seconds` (really played) | `document_id, clip_index` — object id = the clip's `chunk_id`; emitted only after actual playback; exposure only, never evidence (P7) |
| assigned / measured | `arm, metric, value, n` (+ for `measured`: `n_units` = independent assigned units with data, `n_events` = raw events behind them; `n` equals `n_units` since analysis v2) | `experiment_id`, `analysis_version` (`v2` = unit-level analysis, 2026-09-20) |
| degraded | — | `from_alias, to_alias, reason` |
| invalid_output | — | `task, model, attempts` |

## Derived views (create as SQL views in a migration)
- `v_retention_by_representation` — reviewed outcomes joined to the `explained` event that introduced the item, grouped by representation.
- `v_block_engagement` — block_ended.actual/planned and switched_early by block_type × mode × energy.
- `v_calibration` — attempted.confidence_pre vs correct.
- `v_preference_pairs` — preferred events with both explanation texts (for SFT/ORPO export).
- `v_cost_by_task` — from llm_call_log.

Adding a key: document it here in the same commit. Removing/renaming: never — add a new key and stop writing the old one.
