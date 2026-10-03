# Notebook answers follow tutor focus

Selecting a named tutor step previously left the answer textarea bound to the selected editor cell while the tutor received the chosen step’s separate draft. A learner could type an answer and send a blank or older answer for another target.

The focus selector now precedes the answer box. A visible, accessible target names the step/cell being answered. Editing and tutor submission share the same per-cell prediction map; changing focus restores its own answer. Editor selection, code, execution and existing storage format remain unchanged. Reload retains drafts; tutor focus itself still defaults to following the selected cell.

Verification: 12 notebook component tests (46 integrated tutor/feedback tests), ESLint, TypeScript and production build pass. The isolated task-notebook browser journey verifies the exact focused answer sent to the fake tutor, switching back to the other draft, local Python execution and return with preserved project notes at narrow width. Test locators were corrected to accessible textbox/combobox roles and the actual Review my answer label. Independent code/pedagogy review found no blockers or majors. Sanitized checkout: 46 component tests and TypeScript pass. This fixes answer attribution in the interface, not the semantic accuracy of generated feedback.
