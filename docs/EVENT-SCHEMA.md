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
| object_type | TEXT | `item` \| `node` \| `turn` \| `block` \| `session` \| `explanation` \| `adaptation` \| `note` \| `experiment` |
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
| block_started / block_ended | `actual_min, switched_early, reason?` | `block_type, planned_min, node_ids` |
| asked | — | `text_len, node_id` |
| explained | `sentences, cited_sources[]` | `representation, hint_count, model, route, prompt_version, latency_ms, tokens_in, tokens_out, cached_tokens` |
| preferred | `chosen_id, rejected_id, reason?` | `representation_chosen, representation_rejected` |
| attempted | `correct(bool\|null), confidence_pre(1–5), latency_ms, hint_count, answer_len` | `item_type, node_id` |
| graded | `criterion_results[{criterion,passed}], score(0–1 derived), misconception?, confidence, feedback_len` | `grader_level ∈ deterministic|rubric|local|hosted, prompt_version, rubric_version` |
| evidenced | `skill_id, dimension, score, weight` | `attempt_id` |
| proposed (adaptation) / decided | `decision ∈ try|default|no|never` | `what, why, origin ∈ observed_pattern|planner` |
| reviewed | `rating(1–4), latency_ms, predicted_retrievability, days_since_learned, stability_before, stability_after, confidence_pre?(1–5)` | `item_type, node_id` |
| adapted / undone | — | `what, why, reversible, policy_version` |
| parked / promoted | — | `node_id, promoted_to?` |
| spoke | `stt_ms, llm_first_token_ms, tts_first_audio_ms, total_ms` | `stt_model, tts_model, lang` |
| practiced | `duration_min, self_rating(1–5)` | `domain, activity, notes?` |
| assigned / measured | `arm, metric, value, n` | `experiment_id` |
| degraded | — | `from_alias, to_alias, reason` |
| invalid_output | — | `task, model, attempts` |

## Derived views (create as SQL views in a migration)
- `v_retention_by_representation` — reviewed outcomes joined to the `explained` event that introduced the item, grouped by representation.
- `v_block_engagement` — block_ended.actual/planned and switched_early by block_type × mode × energy.
- `v_calibration` — attempted.confidence_pre vs correct.
- `v_preference_pairs` — preferred events with both explanation texts (for SFT/ORPO export).
- `v_cost_by_task` — from llm_call_log.

Adding a key: document it here in the same commit. Removing/renaming: never — add a new key and stop writing the old one.
