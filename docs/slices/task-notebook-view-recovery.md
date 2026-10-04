# Task notebook view recovery

2026-10-04, C3. Reproduced in isolated390px browser: a ready task notebook disappears on refresh, returning to the task despite saved notebook edits. Project course/section was already remembered; the inner notebook view was not.

The existing project work record now optionally stores the notebook/dataset path pair. Only a matching pair reopens the view within that course/section. Explicit return clears it while preserving notes and any deliberately returned summary. Changed paths require explicit reopening and disclose the mismatch. Older records open the task normally. Storage errors stay visible in the notebook rather than disappearing with the task form. No code executes on restoration, and execution results are not recovered or certified. Existing notebook content-keyed edit recovery remains separate.

Verification:8 focused component tests, lint/types/build and3 original browser journeys (desktop/narrow timeout/retry/reload plus existing local execution and checked return). Recovery journeys retain selected cell, prediction and project notes; Return with results stays disabled before a new run. Keyboard return and both responsive screenshots inspected. Code and pedagogy reviews found no blockers/majors; restored wording clarifies view/notes versus results. Existing build warnings remain.

Limits: path equality is not immutable file-content/version evidence; unchanged paths may serve updated content. Existing notebook edit baseline behavior is unchanged. No model quality, screen-reader or owner-comprehension pass is inferred. Full C3, contextual audio mapping and persistent tutor C5 remain open. Next reconcile remaining context-entry contracts with the source/version model rather than adding arbitrary tool links.

Sanitized verification initially lacked the ignored Pyodide runtime: recovery tests passed but execution could not complete. Installed the pinned runtime with make pyodide before repeating execution verification; runtime assets remain excluded from Git.
