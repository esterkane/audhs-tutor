# Notebook upload responsive sizing

GitHub Chromium's 390px conversation journey failed the horizontal-overflow assertion while local default-font runs passed. Reproduction: enlarge the native file input text to 20px at 390px; the notebook grid expanded to x=407, pushing the surrounding controls beyond the viewport. The file input had only display:block and contributed its browser-dependent intrinsic width to the grid.

Constrain the upload input to available width and allow the notebook card to shrink. Preserve native file selection, complete filename access and all tutor behavior; do not hide page overflow or relax the viewport assertion. The journey now reports offending elements and exercises larger native input text as well as desktop behavior.

Validation: all33 isolated local Chromium journeys pass, including the previously failing stress case; lint/types and production build pass. Independent code review: no blockers/majors. No backend or pedagogy changes; existing191 frontend/421 backend test baselines remain applicable. Public Linux CI confirmation follows publication. The full suite still logs the previously recorded unrelated duplicate-key warning during session clarity.
