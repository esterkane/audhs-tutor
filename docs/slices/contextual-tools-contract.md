# Contextual tools: implementation boundaries

2026-10-04 inspection. Playground persists code/prediction/chat by activity, but selected activity resets to scratch. Run output is temporary. Tutor requests send generic activity.task and current session, not a verified originating lesson. Merely adding a lesson link would falsely suggest context preservation.

First preserve selected activity with URL history and explicit invalid-target feedback. Then add a typed origin contract (session/skill/item identity, safe local return URL, source/context snapshot), validate it against current session before tutor submission, and isolate conversations/drafts by origin. Preserve standalone exercise drafts; never overwrite them with starter code. Returning must resolve current phase without creating a session or claiming completed checks. Define stale/deleted origin, storage failure and source-access behavior before passing source content. Visualizer also needs source/playback return handling separately.

No runtime lesson-context transfer is implemented by the selection step. Full C3 remains open.

## Lesson-linked experiment implementation in progress

Lesson entry and local return now exist with isolated session/skill draft and recovery identity, goal text passed as exercise context, and navigation identity explicitly distinguished from retrieved sources. Initial two desktop/narrow round-trip tests pass. Before publication: verify tutor payload and changed-session preflight, pending-send/unmount behavior, independent code review, final visual and regression checks, sanitized validation and paired publication. Stored source snapshots and automatic starter generation are not added by this slice.

Review checkpoint: independent review found recovery retries bypassed context preflight. Shared verification now gates both new sends and immutable retries, with a combined busy guard. A changed-context retry regression and final review remain required before publication. Pending preflight cancellation/duplicate click test passes; unsent questions are now stored with the isolated draft.

## Verified lesson experiment checkpoint

The checks above are now complete for this bounded slice: 17 focused unit tests, lint/types/build, independent retry review, and four desktop/narrow browser journeys in both checkouts. See [lesson experiment](lesson-experiment.md) for behavior and limits. Full C3 remains partial: source snapshots, project/review entry and persistent tutor are still outstanding.
