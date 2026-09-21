# Slice: curriculum-eligibility (P1, 2026-09-20)

**Story.** Once the AI/ML graph is mastered, `next_skill` used to fall through to the vocabulary deck node (a language-domain `skill_node` with no LearningObject or assessment set) and offer it as the next teaching skill (review finding 4). Teaching selection is now restricted to *teachable* nodes; decks stay in the language practice block.
**In/out.** `skill_graph.teachable(node)` = `assessment_requirements_json.teachable` is not `false`; `next_skill` filters on it (every call site — plan, sessions, tutor, assess, challenge, skills — benefits). `practice.vocab_deck` marks deck nodes `{"teachable": false, "kind": "vocab_deck"}` and heals older rows on access; migration `5798bbccbea6` (data step only) marks decks created before P1. Nothing filters by domain: a genuine language *lesson* node (default `teachable`) is eligible, so future language lessons are not blocked.
**Events.** None.
**Mode/energy.** Unchanged; the language block still asks `memory.due_items(domain="language")` explicitly.
**Verified by.** `test_session_transitions.py::test_next_skill_skips_vocab_decks_but_not_language_lessons`; `make migrate-check` applied `5798bbccbea6` to a copy of the dev DB.
**Review fixes (2026-09-20).** None required; both reviewers passed the slice. The pedagogy review confirmed a language *lesson* node stays eligible (test `test_next_skill_skips_vocab_decks_but_not_language_lessons`).
