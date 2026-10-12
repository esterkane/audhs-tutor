# AU-EXPERIMENTS-01: honest experiment read recovery

The learner must distinguish unavailable experiment data from a confirmed empty list.
Query state owns loading/error/data; existing local state owns the opened result. Reads
use the existing 15-second boundedRead helper; no API, schema, learning events, model,
mode/energy, assignment, metric, or assessment changes. Recover through explicit retry;
cached data remains visible with a stale-data notice. Use existing tokens and controls.

Reproduction: opt-in current-app audit received503 but showed “No experiments yet”; a
results failure left “Loading results…”. Two component regressions failed before the fix.

Implementation is limited to the Experiments route and read hooks. Four component tests
pass, including cached list/results retained on failed refresh. Three isolated browser
journeys pass:390/1280px read recovery and keyboard retry, and results recovery with
focus restored. Targeted ESLint, TypeScript and production build pass; existing large
chunk warning remains. Both error-state screenshots inspected: readable and no overflow.
Two review findings fixed: retain the retry control through pending/failed retries and
keep the results focus target mounted across recovery. Final code review: no further
findings. No teaching content or learning-policy change; no pedagogy gate claimed.

No migration; rollback consists of reverting the slice. Real assistive-technology and
human comprehension acceptance remain open. Other audit findings and tutor latency
are separate work. Retry only repeats GET reads, never a start/stop/create action.
