# Checked calculations in source-based research

2026-10-24. The previous bilingual-persona release passed every GitHub gate.
This slice removes generation for a closed calculation that the application can
answer completely; broader research continues through the existing tutor.

## Scope and trust boundary

Direct English/German questions about up to three repetitions of one literal
Python string can return checked values, an unchanged-original statement and a
concise bilingual rule. This uses the existing bounded literal recognizer; it
never executes uploaded Python or source instructions. Custom requests, selected
personal memories, unresolved questions, long sources, ambiguous assignment,
mutation, unsupported syntax or requests for extra explanation retain the model
path and its full existing context. Illegal assignment names, non-ASCII numeric
tokens and leading-zero nonzero literals now defer rather than being accepted by
text-to-integer conversion.

The stable rule follows Python's documented [sequence operations](https://docs.python.org/3.12/library/stdtypes.html#common-sequence-operations).
It explains observable string repetition and preserves all requested results.
It does not invent object allocation, implementation motives or the origin of a
learner's mistake. The calculation uses the source's literal assignment as input;
it does not certify the truth of other source statements. A conflicting reported
result cannot replace the computed value.

Checked replies have a versioned calculation identity and a null model-call ID.
No fictitious inference/cost row is created. The UI identifies the method, labels
the quotation as calculation input and keeps the existing explicit draft-acceptance
step. It offers broader tutor help through the request field. Repeating an unchanged
calculation reuses the signed result instead of filling history with alternatives.
Language/source/question/action changes rebind it. Historical model replies retain
their content and identity; the new optional calculation field is omitted for them.
No competency, grading, model assignment or hosted configuration changes occur.

## Measurements and verification

Four matched fresh API cases (English/German × discussion/draft), using identical
synthetic questions and sources, took 11.297/5.939/7.594/7.471 seconds before this
change and 0.020/0.013/0.014/0.013 seconds afterwards. The baseline German discussion
also returned English and added an unsupported allocation explanation. The checked
replies cover all values in the selected language without that claim. These are
narrow observations; general tutor generation is not accelerated by this slice.

Final calculation/parser/research tests: 99 pass, including all fallback contexts,
history preservation, language changes, no-model/no-learning-evidence assertions,
legacy serialization and illegal-syntax deferral. Frontend full suite: 770 pass;
after the recovery correction, all 23 affected component/recovery tests pass.
TypeScript, ESLint, Vite, Ruff and strict mypy pass. Full backend: 2,288 pass, one
intentional skip; the final 99 affected tests include ten later syntax-hardening
regressions. Browser: six sandbox journeys
pass, including desktop English/mobile German checked-reply reload and continued
editing.

Both isolated complete browser workflows pass: upload → linked questions → findings
→ discussion → section → explicit acceptance → Write → Review → save/reload →
activation. Each retains both replies and exact input quotations. UI request times
were 0.737/0.262 seconds (German) and 0.696/1.022 seconds (English), including save
and browser overhead. Accepted reading, practice feedback, saved notes and session
resume are then checked for both lessons. No real learner data is used.

The first browser run caught a recovery validator that still required a model-call
ID and therefore made a restored checked draft read-only. The validator now accepts
only coherent model/calculation identities, with unit and browser regressions.

## Remaining work

Two live broader object-identity follow-ups correctly reached the model and kept
the earlier checked replies and exact input quotation, but both incorrectly
claimed immutability entails fresh objects. They took 15.001/11.149 seconds. Their
answers are retained as failures, not accepted content or evidence of improved
general reasoning. No unchanged prompt trial or production model switch follows
from those failures.

Broader paraphrases, causal claims and model waiting time remain open. Source
quotations alone do not establish semantic correctness. This slice is compatible
with a future authoring/review phase using configured hosted models and an everyday
learning phase that retrieves accepted, versioned material first. Hosted models
still need source-based verification; updates should be proposed against saved
versions rather than silently rewriting accepted lessons or session history.
