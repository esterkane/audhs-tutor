# Distinguish retained ratings from recovery

Completed 2026-10-13. Visual inspection found archived-only ratings still used warning styling and told learners to check a submission after recovery had finished. The panel now uses the existing neutral border token, Previous review ratings heading/region and reference-only explanation when there is no pending rating, recovery error or memory-only mode. Active recovery retains all controls and warnings; archived choices and dismissal remain available. No learning logic changes.

Validation:35focused hook/Review tests; two real sandbox desktop/narrow refresh-and-rate journeys including keyboard submission, resolved heading and absent obsolete warning; screenshots visually inspected; no horizontal overflow; targeted lint and type/build pass. Existing build size warning remains. Code and pedagogy reviews found no blockers or majors. Broader R4 and manual assistive-technology checks remain open.
