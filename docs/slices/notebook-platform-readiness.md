# Notebook platform readiness

## Scope — 2026-10-25

Release bd591a5 completed every GitHub CI gate successfully. Continuing the notebook usability
checklist exposed a false-positive readiness case: the static check treated membership in
sys.stdlib_module_names as proof a module existed. That set also includes platform-inapplicable
and build-disabled modules, as documented in the [Python reference](https://docs.python.org/3.12/library/sys.html#sys.stdlib_module_names).
For example, Windows-specific winreg must not be reported available merely because Python
recognizes its standard-library name when the notebook runs on Linux.

The isolated -I/-S/-B metadata probe now checks actual built-in/frozen module availability and
module specs along the interpreter's isolated standard paths plus the explicit notebook-venv
package locations. Finding specs never imports the target packages. The standard-library name
set is used only to classify modules already found missing. Local helper files retain their
existing separate handling. No cells, packages, site hooks or installation commands are run.

The backwards-compatible unavailable_standard_imports result separates missing interpreter/
platform modules from other missing imports. The optional notebook panel explains this distinction
without suggesting an ordinary pip package will necessarily resolve a platform limitation.
Older cached/result shapes remain usable; the new list defaults to empty. The check still
reports location evidence only, not successful runtime imports or valid learner exercises.

Malformed course-bundle lists or non-string filenames now return the existing recoverable
unavailable result rather than an uncaught attribute error. Bounded file reads, path/symlink
guards, read-only/no-store API behavior and raw-content exclusion remain unchanged. API types
are generated from OpenAPI. There is no database migration or learning-state/model-policy change.

## Verification

- 30 notebook backend tests pass, including real temporary-venv built-in/standard/extension/
  third-party lookup, a missing platform module, poisonous package non-execution and five
  malformed manifest shapes.
- Six notebook UI tests pass, including old result shapes and platform-only missing modules.
- Twelve browser journeys pass: phone/desktop readiness with both missing-module categories,
  keyboard, axe and reflow; research→section→save/reload→Review; accepted lesson→assessment→
  feedback→recap; real offline Python and session boundary/review/resume flows.
- Ruff, formatting, strict mypy, TypeScript, affected ESLint and production build pass.
- A prepared local working copy stays byte-identical and its existing scientific imports are
  still located. No course cell, exercise or install command was executed.

Existing fully green release CI is reused for unchanged components; new release CI remains a
separate snapshot gate. Main progress, histories, credentials, routing and the hosted-authoring
cap are preserved. The current local-model preparation path already covers research authoring;
no duplicate warm-up path or speculative performance change was added. Broader local-model
accuracy/decoding latency, original-course exercise completion and cross-browser acceptance
remain open, not implied complete by this bounded notebook slice.
