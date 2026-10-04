# Notebook pause retains completed work

Reproduced in the isolated project-learning journey: Run all and check succeeds, Pause study, Resume this step disables Return to task with results. Pausing unmounted the entire workspace and discarded its completed run.

Task and full-notebook containers now preserve Workspace state while paused. Workspace hides its children (stopping tutor/audio components), stops active execution and rejects late completions. Already finished output/checks and edits remain for resume. Reload still restores editable sources only and requires a new run; no persisted browser output is treated as verified execution.

Verification: failing-before/passing-after real Python browser journey through notebook run, explanation feedback, pause/resume, return to notes and reload; 13 workspace unit tests including active-run disposal/late completion; TypeScript and focused lint. Tests use synthetic materials and sandbox data. Physical audio and owner comprehension are separate open gates.
