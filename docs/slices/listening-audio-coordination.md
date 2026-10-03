# Listening clip audio ownership — 2026-10-03

Explicit clip Play/Replay claims the existing in-tab foreground audio lease. A reading or voice
activity replaces it by pausing, preserving clip position and showing why; resumption is explicit.
Manual pause keeps shared Resume clip available. Shared Stop clip pauses/releases without ending
learning or resetting position. Stop here retains its existing lesson-exit meaning.

Audio controls identify Listening clip and expose supported Pause/Resume/Stop. Volume and rate
remain bound to existing preferences. Terminal media/error/unmount releases ownership; request
identity fences old play resolutions/rejections so they cannot pause or overwrite a newer play.
No automatic resume, model calls or grading change. Exposure increments only on time updates during
confirmed active playback; paused seeks do not manufacture listened seconds.

Verification: full frontend336/83files; ListeningPanel8 tests including replacement/position/exposure,
late resolution and rejection after new resume, shared pause and terminal release. Existing rejection
and unmount tests retained. TypeScript and changed-file ESLint passed.
Isolated browser coexistence journey1 passed on8061/5225 with a test-only composition of production
ListeningPanel/ReadAloud/shared controls, fake HTML media and silent AudioContext, held synthesis.
No real audio/microphone/models or live DB changes. Test fixture is not imported by production code.

Independent code and pedagogy reviews clear. Integrated frontend338/84files, two coexistence browser journeys, TypeScript/fullESLint/build passed; sanitized focused20 plus TypeScript passed. Visualizer, ambient and test-tone ownership remain
separate outstanding slices; Bluetooth audibility and owner comprehension remain unverified.
