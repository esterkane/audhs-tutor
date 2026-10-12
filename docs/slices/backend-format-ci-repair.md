# Backend formatting CI repair

2026-10-12: run38246692258 failed the backend job at `uv run ruff format --check .`.
Ruff lint passing alone did not satisfy that separate gate. Six currently tracked
Python files needed formatting: grader, assessment provenance/request tests, hosted
trial/preflight tests and Progress evidence tests. Applied Ruff formatting only;
Python AST comparisons against HEAD are identical for all six files.

Exact local backend-cwd gates: `uv run ruff check .` passes;
`uv run ruff format --check .` reports414 formatted files; `uv run mypy app`
passes229files;54 affected tests pass4.23s. No paid calls or routing changes.
Reuse existing browser/build evidence because Python semantics are unchanged.
Always include the formatter gate alongside Ruff lint before publication.
Remote latest-head completion remains separate from these local checks.
