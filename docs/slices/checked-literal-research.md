# Checked literal-expression research

## Scope — 2026-10-25

Closed Python-3 code-output questions can now use a bounded local calculation instead of
generating arithmetic/type behavior. This broadens the earlier string-repetition calculation
to numeric arithmetic, string/list/tuple concatenation, sequence repetition and the supported
TypeError/ZeroDivisionError results. It does not change the general tutor model or improve its
raw decoding throughput. Broader causal/statistical reasoning remains open.

Example source passage:

```python
label = 'Tag '
```

Question: What do `label + 4`, `4 + 2.5` and `[1] + ['x']` return?

The checked answer reports TypeError for str + int, 6.5, and [1, 'x'] in the selected English/
German response language. It answers each expression once, without guessing a learner mistake's
origin or inventing an allocation/implementation cause. Its provenance is explicitly a checked
calculation; the source quotation supplies the input, not proof of every source claim.

## Admission and execution boundary

Only a complete backtick-delimited output question is recognized (English What do/does…return/
produce/evaluate to? or German Was geben/gibt…zurück?). The whole source must be a single Python
code fence or start with Python 3: followed by literal-only, non-reassigned bindings. Other
prose, control flow, imports, calls, mutation, attributes, subscripts, unknown names, broader
requests, unresolved issues and selected personal memories defer to the existing model path.
No supported expression is silently omitted if another expression cannot be handled.

The pure kernel helper parses a bounded AST and invokes trusted arithmetic operators only on
exact built-in literal types. It never evals/executes uploaded source or invokes user callables.
Expressions, AST nodes, assignments, depth, numeric magnitude, repetition sizes and output are
bounded. Exponentiation and string formatting are excluded. Notebook files and original input
bindings are unchanged. This is a small checked computation path, not a Python execution sandbox.

Existing public replies and histories retain their schema. A versioned calculation identity
adds python.literal-expression.v1, exactly one of model/calculation/reference. Source, action,
presentation and result participate in signed reuse. Broader/custom help still receives the
existing full packet and model route. Exact calculations require no hosted reservation even
when hosted authoring is enabled. Writing, explicit paragraph use/save and activation remain
learner-controlled; no assessment or competency evidence is created.

## Evidence and limits

Controlled test expressions and a built-in operand/operator matrix are independently compared
with Python results, including actual exceptions. Developer-owned test fixtures alone use eval;
production does not. Tests cover conservative deferral, allocation limits, source-instruction
non-execution, bilingual output, legacy history/reuse and enabled-hosted zero-inference controls.
API types are generated from OpenAPI; browser recovery recognizes the new identity and rejects
mixed/unknown identities.

The two checked browser replies arrived in 106/90 ms, covering English/German paragraph use,
Write, save/reload and Review. Same-question native model baselines took 12.011/16.643 s and
returned the core results but added recap prose. These use different timing boundaries (whole
checked UI interaction versus provider gateway), so no universal speedup factor is claimed.
The improvement is avoiding unnecessary generation for admitted calculations.

Formatting follow-up: question keywords/separators and Python source headers are recognized
without case sensitivity; LF and Windows CRLF source wrappers are supported. Multiline question
layout, ASCII padding around an expression and German zurueck spelling are accepted without
case-folding identifiers or collapsing whitespace inside strings/code. Unterminated fences,
unsupported names/calls and broader questions still defer as a whole. German error prose uses
the complete transitive form verursacht. Controlled tests preserve mixed-case names, Unicode
string values and repeated spaces, including an empty Python fence.
Follow-up verification: 65 calculator checks and 197 affected research/authoring tests pass;
all 11 browser journeys pass, including CRLF/lowercase English/German save/reload/review and
lesson/feedback/recap/resume. Checked UI replies measured 100/81 ms in those two cases. This
expands reliable admission, not the model's raw decoding speed. No arbitrary code or wider
context is admitted merely because grammar capitalization or line endings were changed.

A separate three-case open-ended model canary exposed an evidence-qualified impossible event
order, an unjustified randomized-study condition and an unevaluated requested numeric result.
A targeted guidance trial corrected some points but added a source-free causal scenario and
increased mean generation time. It was rejected without changing deployed prompts. Raw trials
and every attempt remain in private evaluation records. No general accuracy or decode gain is
claimed. See the [current backlog and open questions](../QUALITY-BACKLOG.md).

Full backend regression: 2,432 passed / one skipped. The final 58 calculator checks pass after
whole-expression admission hardening, including the controlled operand matrix and old-history/
enabled-hosted controls. Full frontend: 797 passed. All 14 affected workflow browser journeys,
Ruff/format, strict mypy, TypeScript, ESLint and production build pass. These include saved
authoring/reading, assessment/feedback/recap, notebook readiness and offline Python. Whole-expression
validation also rejects unsupported calls/names even if an earlier operand would raise first.

Publication checks and exact-release CI state are recorded in the local handoff. Main histories,
accepted material, credentials, budgets and private archive are preserved. The raw model policy,
reasoning settings, target weights, context limits and output ceiling remain unchanged.
