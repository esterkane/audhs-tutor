# Recover local task-notebook loading

Opening a task starter loads a notebook and optionally its dataset. Previously these requests had no deadline, so a stalled local file request could leave the loading view indefinitely. Partial state could also retain an earlier prelude when sources changed.

The loader now treats validated cells, calculation checks and dataset prelude as one result. Each attempt has a bounded deadline, cancellation and stale-response protection. Retry starts a fresh attempt; Back remains available throughout. Changing the source remounts the loader so an earlier source cannot remain visible as the new workspace. Existing notebook drafts and project notes retain their established storage keys.

This does not execute cells, install packages, alter the source notebook, or claim that a loaded notebook is correct. A clean load only means its local starter and selected dataset are ready for the learner's explicit next action.

Verification: 17 focused task/notebook component tests, ESLint, TypeScript and production build passed. Three isolated browser journeys cover stalled dataset retry at 1280px/390px, preserved task notes and the normal local execution/checked-return flow. Tests include stalled notebook and dataset responses, source changes removing old data, late completion and unmount. Independent review found no blockers or majors. Existing production build warnings remain; no live learner session, notebook execution outside the synthetic sandbox, or model request was used.
