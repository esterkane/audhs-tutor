# Shared button design adoption

2026-10-04. Adopted uploaded Button specification: secondary/outline controls use control borders, primary hover uses accent-hover, quiet actions use accent text, disabled labels use faint on sunken without opacity fading. Existing variants and large size remain supported. Heights are minima with vertical padding, preserving target size while allowing wrapped text. No learning/action logic changed.

Eight lesson browser cases passed across explicit/system themes and 390/1280 widths, including large text, reduced motion, disabled over-length input, keyboard focus/input and pause/resume draft retention. Lint, TypeScript and build passed with existing bundle/worker warnings. Narrow dark screenshot inspected: labels and borders visible, no horizontal overflow. An initial new assertion incorrectly expected the empty-input button to have its typed-question label; corrected the fixture to exercise the actual over-length disabled state.

Remaining: not every caller uses this primitive; no blanket component-conformance claim. Full typography, panels and contextual shell remain pending. Faint is restricted here to disabled controls, not instructional text. Large size and outline are retained compatibility variants.
