# Local arithmetic checks for workspace feedback

Status: implemented and verified; wider formative-feedback quality remains open.

Before non-hint feedback on a submitted answer, check bounded literal numeric equalities locally. Support decimal/integer arithmetic with +, -, multiplication, division, parentheses and percentages; never execute learner code. Show the exact expression and calculated values separately from model guidance, persist the checks and original model output, and read the same disclosure aloud. Do not grade interpretation, task completion or mastery. Hints do not expose solved calculations; mode and sensory preferences remain unchanged. No dependency, route or database migration.

Baseline: the pinned v7 local trial explicitly endorsed `30/50 = 0.9`. Correct answer binding does not prevent false mathematical feedback. A deterministic displayed result must survive model disagreement and saved-answer reopening. Unsupported syntax remains unverified; checking a literal equality does not say whether the learner endorsed it or whether its application to the task is valid.

Acceptance: wrong/correct/percentage/negative/parenthesized values, unsupported and ambiguous syntax, zero division, bounded adversarial input, quoted hypothetical math, injection, hint withholding, persisted raw+checked output, replay, no competency writes. Run regression suites, independent code/pedagogy review and a separately labelled local-model diagnostic.


## Supported scope and abstention

The checker accepts complete literal numeric equalities at line starts or explicitly quoted/semicolon-separated boundaries. It evaluates integers/decimals, unary signs, +/−, multiplication/division, parentheses and percent literals with exact rational arithmetic. It returns at most six checks from an at-most 8,000-character answer. Each side is capped at 128 characters, each number at 12 digits, and parsed AST size at 48 nodes. No eval, execution, network, model or database call occurs in the kernel checker.

Word/colon prefixes, named functions, roots, factorials, powers, variables, units, comma decimals, approximate/chained notation, incomplete expressions and zero divisors remain unverified. Code is masked with nonnumeric boundaries. A rounded decimal may fail exact equality: the notice explicitly says exact, not approximately equal. Prose such as “I got 30/50 = 0.6” is conservatively not checked; a standalone or quoted equality can be checked. No result means unsupported/unverified, never a pass. Literal quoted errors are not assumed to be the learner's belief.

Checks are computed both for prompt context and final disclosure. The model cannot remove the final notice. Saved text and read-aloud share that notice, and metadata retains original raw model text, individual checks and checker version. Prompt v8 invalidates earlier exact replay; reopening a new saved reply retains its historical notice and makes no new model call. Hints receive no solved checks. No mastery, assessment or evidence record is created.

## Review fixes and verification

Independent review found partial suffix extraction of unsupported root/ratio/bitwise/code/function/factorial notation. Replaced permissive boundaries and function-name guessing with conservative admitted boundaries, added matching quote checks and regressions, and fixed decimal display. Final re-review found no remaining blockers/majors in this scope.

- Full backend: 542 passed; full frontend: 228 passed, including same delivered text passed to read-aloud (not a speaker/device playback test).
- Final lint, formatting, mypy, TypeScript and ESLint passed.
- Focused tests include wrong/correct percentages, exact decimal arithmetic, unsupported syntax, injection boundaries, bounded input, quoted hypothetical claims, hints, persistence, wrong-model disagreement, zero-call exact replay and no learning evidence. UI implementation did not change; the preceding desktop/narrow journey/build evidence is not claimed as rerun here.

## Local-model evidence

Twelve real pinned Gemma calls across three four-case diagnostic runs are preserved in `evals/results/answer-memory/arithmetic-v8-{initial,before-decimal,final}.json`. Final request-message hashes were rechecked against current code after boundary fixes. The final four-case run includes the actual finalizer output as well as raw model output.

In the final run, wrong 30/50 = 0.9 was correctly corrected to 0.6 / 60%; the app's deterministic notice independently shows 3/5 (0.6) versus 9/10 (0.9). The hint supplied no solution. However, internal tags still leaked in the raw wrong-answer response, the opening ratio wording was weak, and the correct-answer response still invented a fraction-versus-percentage objection. This is not a general teaching-quality pass or routing comparison. No hosted call or live routing change occurred.

Remaining: supported attribution validation, richer interpretation/rubric feedback, wider local quality evaluation, and the saved-answer recovery/correction queue. Main lesson assessment remains separate; this does not claim every mathematical claim across the platform is checked.
