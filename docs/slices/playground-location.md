# Playground location recovery

2026-10-04. Selected activity previously reset to Free experiment despite independent saved code. Selection now uses the workspace URL parameter. Changes preserve other parameters and enter browser history; refresh and Back/Forward restore the selected activity and its existing draft. Unknown IDs show explicit fallback feedback without overwriting other drafts.

Six existing playground tests pass before and after. Two desktop/narrow browser cases verify deep links, separate saved code, reload, Back/Forward, unknown IDs, no API writes and no overflow. Keyboard focus was checked; native selection was exercised with Playwright selectOption after the OS-specific Home-key assumption failed. Lint/types/build passed; existing canvas and bundle/worker warnings remain. Narrow screenshot inspected.

Full lesson context transfer is not implemented. See contextual-tools-contract.md before adding lesson/tool links: tutor context and draft/chat identity need an explicit origin contract. Run output remains temporary.
