# Contextual tools: implementation boundaries

2026-10-04 inspection. Playground persists code/prediction/chat by activity, but selected activity resets to scratch. Run output is temporary. Tutor requests send generic activity.task and current session, not a verified originating lesson. Merely adding a lesson link would falsely suggest context preservation.

First preserve selected activity with URL history and explicit invalid-target feedback. Then add a typed origin contract (session/skill/item identity, safe local return URL, source/context snapshot), validate it against current session before tutor submission, and isolate conversations/drafts by origin. Preserve standalone exercise drafts; never overwrite them with starter code. Returning must resolve current phase without creating a session or claiming completed checks. Define stale/deleted origin, storage failure and source-access behavior before passing source content. Visualizer also needs source/playback return handling separately.

No runtime lesson-context transfer is implemented by the selection step. Full C3 remains open.
