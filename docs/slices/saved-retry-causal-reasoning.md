# Explaining saved retry decisions from verified observations

A local model answered the recorded full-retry question by inventing a Repeatable Read
versus “write-consistent UPDATE-only” distinction. The saved result instead supplies a
direct explanation: the full retry made a new read, evaluated the business predicate,
and made a decision; commit success is a separate recorded outcome.

The existing source-bound report renderer now supports causal wording for explicit
questions comparing full retry and UPDATE-only decisions in identified saved experiments.
Both retries must exist. The same validated source bindings and host `count > minimum`
comparison supply every value and predicate. The renderer says why that recorded business
decision followed; it makes no new claims about isolation guarantees, snapshot identity,
SQL execution or the learner's understanding. A false question premise does not overwrite
the observations. Final counts and minimum satisfaction remain distinct from the decision.

The bounded language frame requires both retry strategies, a commit/decision question and
an unambiguous literal saved-experiment reference. Mixed, unfamiliar, hypothetical or broader
causal requests retain the complete ordinary tutor path. Active labs, incidents, exams and
Socratic delivery also retain that path. No second model paraphrases the verified answer.

## Verification

- 357 scoped backend tests passed, including 24 new causal-frame/renderer tests.
  Strict mypy (349 application files), Ruff, TypeScript and changed-test ESLint passed.
- Parameterized English/German tests vary workers, minimum and first commit actor, including
  cases where the question's “did not deactivate” premise is false.
- Missing retries, inconsistent observations, uncovered questions and active learning modes
  delegate rather than invent a cause. Full original questions and histories remain intact.
- Isolated browser workflows execute four local experiments per language, compare reports,
  ask causal follow-ups for two different experiments, and verify exact save/reload plus
  unsent draft retention. English causal replies measured 169–170 ms; German 165–182 ms.
  These are local machine observations, not a general latency guarantee.
- The full authoring/upload/reading/notes/feedback/resume regression passed (19.8 seconds).
  Five existing incident, reference and save/resume browser regressions passed (29.6 seconds).
  An independent persistence check confirmed 60 raw messages, eight actual experiments and
  40 independent trials retained in two isolated sessions, with eight local embedding calls
  and zero chat/hosted calls. Browser accessibility checks passed in desktop English and
  narrow-screen German layouts.

This expands accurate local reuse for recorded decision arithmetic. Broader unfamiliar
incident explanations and local free-form generation quality remain outstanding.


## Equivalent German constraints

The held-out phrasing “im selben Versuch” with “Kein neues SQL ausführen” now reaches the same
verified causal report. Equivalent negative execution and no-invented-observation constraints
are recognized without interpreting positive execution requests as report-only requests.
“No observations” remains distinct from “no invented observations”; uncovered requests still
use the full tutor path. The complete original question and raw history remain unchanged.

The expanded delta passed 365 scoped backend tests. The full German/English experiment,
causal-reply and reload journeys passed (24.5 seconds); replies measured 168–188 ms. Independent
persistence checks retained all 60 raw messages in two isolated sessions, eight experiments
and 40 trials, with eight local embedding calls and no chat or hosted calls.
