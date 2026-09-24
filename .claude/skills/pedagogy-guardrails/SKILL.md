---
name: pedagogy-guardrails
description: Evidence-based tutoring rules and a review checklist for any prompt, grader, scheduler or session-planner change. Claude loads this whenever it writes or edits tutor/grader prompts, FSRS/planner logic, or assessment flows.
user-invocable: true
---
# Pedagogy guardrails

Why these exist (evidence, short): unguarded LLM help boosts practice scores but *lowers* unaided performance (Bastani et al., PNAS 2025: −17% after access removed); hint-scaffolded tutors avoided that harm. A brief, one-step-at-a-time, solution-grounded AI tutor beat active-learning classrooms (Kestin et al., Sci Rep 2025). LearnLM's five principles: manage cognitive load, inspire active learning, deepen metacognition, stimulate curiosity, adapt to the learner. Full report: `docs/research/adaptive-learning-report.md`.

## Checklist (answer each before merging)
- [ ] Hint-first, single step per turn, brief. No full solution unasked.
- [ ] Default explicit explanation; Socratic only when `session.mode_socratic=true`. No silent switching.
- [ ] Literal, direct wording; concrete options instead of open/feeling questions.
- [ ] Citations to corpus (`course › section › lecture @time`) or explicit "no source".
- [ ] Confidence rating captured before feedback on assessed items.
- [ ] Non-punitive, specific error feedback; no praise filler.
- [ ] Worked example → faded problems for *new* nodes; problem-first (productive failure) allowed only for nodes with mastery ≥ 0.6 (expertise reversal).
- [ ] Retrieval practice > re-reading: any "explain" flow ends with a recall item scheduled in FSRS.
- [ ] Interleave *confusable concepts within AI/ML* for learning; switch *domains* (language/guitar/movement) only at block boundaries.
- [ ] Movement block placed before a new-material block or immediately after, never during.
- [ ] Multiple representations (analogy / derivation / code / diagram) offered as *options*; never "learning-style" typing.
- [ ] Optimizes delayed retention (FSRS review outcomes), not satisfaction. Any bandit/personalization reward = review outcome, not thumbs-up.
- [ ] Gamification off by default; progress shown as mastery, no streak pressure.
- [ ] Events emitted with `representation`, `activity_type`, `hint_count`, `confidence`.

## Session template (reference for the planner)
0 movement primer 5–10 · 1 retrieval warm-up 5–10 · 2 new material (worked → faded) 20–25 · 3 critical-thinking challenge 10 · 4 interleaved review 10 · 5 domain switch (language/guitar) 15–20 · 6 confidence-rated recap 5. Minimum-viable session = blocks 1 + 6. Low-capacity mode = 1 + (2 or 4 short) + 6.


Owner decision (2026-09-24): confidence ratings are optional and collapsed by default. Never block feedback, revealing a review answer, stopping, or changing topic on confidence or a grasp check. Omitted confidence stays null; clear/later labels are self-report, not mastery evidence. This supersedes mandatory-confidence guidance above.
