# Notebook guided study

User report: saved notebook is read-only; prompts have no submission path and insufficient context. Replace the reader with editable cells, preceding context, explicit local run/output, export and saved work. Reuse the existing contextual tutor for explanation, optional Socratic questioning and formative answer review. Global opt-in selection read-aloud and dictation keep audio accessible across pages; no autoplay or automatic microphone capture.

Full notebook compatibility uses a separate localhost Jupyter environment, retaining standard notebook outputs, kernels and data files. Browser experiments remain limited; do not claim native scientific libraries work in Pyodide. No automatic execution of imported notebooks. No new mastery evidence; existing tutor trace/event path remains authoritative. Respect mode/sensory choices; keyboard labels and stop controls required.

Verification and remaining scope will be recorded after tests. Course-specific dependency compatibility and content quality require per-notebook checks; a general runner is not proof that every imported notebook executes successfully.

## Verification / review

Implemented editable source, preceding instructions, per-cell answers, saved drafts, source export, explicit fresh local execution with output/error and cancellation. Markdown questions have answer fields too. Contextual tutor receives preceding executed code and actual output separately from the learner answer. Optional Socratic action, read-aloud and review-before-send dictation use existing model/voice boundaries. Shell companion makes passage help available on every route.

Independent code/pedagogy review found and fixed pause hiding live microphone controls, unsaved tutor messages, obsolete response context, missing runtime-load deadline, shared predictions and incomplete notebook context. Tutor identity is scoped by notebook and cell. Browser experiments are standard-library only; exports explicitly omit original outputs/metadata. Complete original notebooks run separately in authenticated localhost JupyterLab.

Real Jupyter installation and kernel execution passed: pandas mean example and assertion. Local course imports and dataset load verified separately; incomplete exercise cells are not claimed to execute end-to-end. Browser UI opened and inspected against the local saved notebook. No live microphone capture or generated-feedback quality evaluation performed. Full platform pedagogical redesign, native kernel embedding, course-specific hidden test suites and automatic correctness grading remain follow-up work.

Final checks: 154 frontend tests passed; ESLint, TypeScript and production build passed; launcher Ruff checks passed. Public staging guard and platform-name scan passed. Test-only Jupyter server stopped after verification; start with make notebooks.
