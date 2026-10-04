# C5 persistent tutor contract

## Baseline evidence

The existing shell keys LearningCompanion by pathname; route changes discard its captured material/open state. Inside it, ReadAloud and StudyTutor share a raw-passage key, and editing the material remounts the conversation on every keystroke. A disposable browser reproduction confirmed an unsent question disappears when the material changes and the companion is closed after a route detour/Back. React also reported duplicate sibling keys.

StudyTutor owns session-scoped conversation persistence and durable request identity. It uses a single response request, not partial token streaming. Unmount aborts the browser wait; this does not establish that server work was cancelled. ReadAloud and DictationButton clean up playback/microphone on unmount. Removing all unmount boundaries or hiding them without media cleanup would change these contracts.

## First bounded implementation

Retain one active captured context across route navigation, with a separate editable material draft. Capture only on explicit action. Clearly name the original page and provide its return link; browsing another route must not silently change the tutor target. Apply material explicitly, and retain the previous captured context for a reversible switch. Existing StudyTutor remains keyed to applied material and session, preserving its history/request isolation.

Keep versioned, bounded tab-local active/draft/previous material checkpoints, validate them on restore, and report storage failure without discarding in-memory work. Opening/reopening never starts sound or a model call. Closing still unmounts request/media children, stopping local waits/playback/microphone through existing cleanup; copy must explain request recovery rather than promise server cancellation. Reopen the retained material and existing conversation. No learning state changes.

Likely files: LearningCompanion.tsx, Shell mount, focused companion tests and browser journeys. No backend, new library or provider change. Verify typing preserves the current question; apply separates contexts; previous-context return restores the old draft; route/Back/reload retain the exact material; storage failures remain explicit; close/reopen retains work; no automatic model/audio requests.

## Following presentation slice

Move the stable companion into the authoritative desktop side panel and narrow-screen sheet with responsive focus management. Do not duplicate the conversation during resize. Keep close/collapse semantics explicit and reachable Stop. If a later collapse keeps an active request mounted, add an explicit external status/Stop interface and suppress hidden focus/microphone activity before enabling that behavior. Desktop navigation must remain usable while the panel is open; mobile sheet must trap focus and return it safely.

The existing lesson streaming tutor is separate. Its partial-response recovery cannot be claimed from StudyTutor tests. Cross-surface conversation unification, live-session changes, route-independent voice and actual owner/VoiceOver acceptance remain explicit gates. This contract does not replace the learning kernel or authorize hosted inference.
