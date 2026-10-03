# Recover stalled answer-feedback writes

Saving a report on a saved tutor answer, or reviewing its latest saved feedback, could leave the editor disabled indefinitely when the request stalled. Each operation now has a 15-second deadline and cancellation; request identity prevents late responses from replacing later edits or clearing their local draft. Unmount cancels outstanding work.

A timed-out write may already have reached the server. The message preserves that uncertainty and asks the learner to review the latest saved feedback before retrying. Existing revision conflicts and explicit saving remain; no automatic overwrite, new API or model invocation.

Verification: five focused timeout/conflict tests pass, including never-completing save/latest requests, late completion and unmount. Integrated 46 component tests, ESLint, TypeScript and production build pass; the sanitized checkout passes the same 46 component tests and TypeScript. Independent review found no blockers or majors. Initial feedback loading remains governed by the existing query lifecycle and is outside this write/review slice.
