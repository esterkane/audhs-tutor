# Lesson-linked coding experiment

2026-10-04. Session offers an optional coding experiment with a visible lesson return link. A matching current session/skill is required; stale/ended links offer Home recovery. Code, prediction, chat and unsent question are isolated by session/skill identity, without overwriting standalone workspaces. Tutor receives goal text, code and navigation identity, explicitly not a retrieved-source claim. No code or sound starts automatically.

Fresh sends and immutable retries refresh the origin before sending. Identity guards prevent duplicate preflight and late sends after stop/unmount. Retry retains original body/key and does not overwrite later questions. The preflight guard is released before the existing model-request lifecycle so ordinary timeout/cancellation behavior stays intact.

17 unit tests, lint/types/build pass, including changed-skill retry rejection, identical retry replay, pending-check unmount and unsent question persistence. Two lesson browser cases verify tutor payload, return draft, reload, isolation and ended origin; two existing workspace-history cases cover standalone regression. Narrow linked-workspace screenshot inspected. Independent review's retry-preflight major was fixed; follow-up review found no further majors. Existing canvas-test and worker/chunk warnings remain.

Remaining: source-grounded contextual retrieval, generated starter examples, project/review entry, immutable content-version tracking and persistent cross-route tutor. This implementation links the current skill goal, not a frozen source/assessment version. Browser origin checking is not atomic with a later server session change; it adds no assessment/mastery writes. Full C3 remains partial.
