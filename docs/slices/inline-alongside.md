# Work alongside within a lesson

2026-10-04. Standalone Work alongside required a route detour and unmounted the lesson. Added an explicit optional inline panel in Session, reusing Together while keeping the lesson mounted. Opening/closing does not write session/learning state or start sound. Closing unmounts the quiet panel and stops its optional ambient sound; the answer stays. Standalone route remains available. Embedded presentation omits duplicate audio settings because the header controls remain available.

Two browser cases at390/1280 verify keyboard toggle, retained input, no learning/API writes, no autoplay and no overflow; ambient audio ownership case also passes. Twelve Session/Together unit tests and lint/types/build passed. Initial screenshot prompted reduced embedded topic sizing and removal of repeated settings. Final narrow screenshot inspected and the three browser cases rerun successfully after the presentation adjustment. Existing canvas-test and worker/bundle warnings remain.

Remaining: full context-preserving tools, review/project entry, persistent tutor and mode navigation consolidation. This is a session entry point, not completion of the entire C3 workspace stage. Physical audio remains unverified.
