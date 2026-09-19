# Slice: preferences-checkpoints (Stage 2)

**Story.** The learner's settings are explicit, typed and reversible; a session survives a reload or a stop and resumes where it was (skill, phase, block, hint level).
**In/out.** `kernel/preferences.py`: closed registry (`session.*`, `tutor.representation_default`, `planner.*`, `ui.*`) with types, defaults, choices, ranges; `set_pref(origin ∈ explicit|proposed_accepted|inferred)` emits `adapted` for non-explicit origins; `reset`. `GET/PUT /api/preferences`, `DELETE /api/preferences/{key}`; `Preferences` screen (concrete choices, sliders for minutes). Checkpoints: the tutor turn writes skill/hint level; the UI merges `phase`/`block_index` via `POST /api/sessions/{id}/checkpoint` (pruned to the newest 3, TTL 7 days); `GET /api/sessions/current` + `SessionOut.checkpoint` drive "Resume session" on Home and initialise the session screen state.
**Events.** `adapted` on inferred/proposed preference writes. Checkpoints are not an audit store.
**Verified by.** `tests/test_stage2_kernel.py::test_preferences_registry`, `tests/test_stage2_api.py` (preferences API, resume after a turn + UI checkpoint), Stage 2 benchmark C.
