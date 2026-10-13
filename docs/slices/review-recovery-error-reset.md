# Clear resolved review submission errors

Completed 2026-10-13. After an explicitly refreshed card was revealed, an obsolete mutation error still instructed the learner to check the earlier submission. Clear now resets the mutation only after identity validation, archival and successful recovery removal. Failed storage operations retain recovery. Rating rules and scheduling are unchanged.

Evidence: baseline regression failed 1/16; final hook/Review tests35 pass. Two real sandbox desktop/narrow journeys pass, including explicit refresh, absent obsolete warning, keyboard rating submission and no horizontal overflow. Screenshots inspected at both widths. Targeted ESLint, type checking/build and bounded code review pass. Existing bundle-size warning remains. Earlier rating archive is retained and never automatically resent.

Remaining: the retained-rating panel still uses recovery-oriented heading/copy even after resolution; broader recovery presentation and R4 acceptance remain open. No model-quality claim or assessment-policy change.
