# Compact header audio with visible playback control

2026-10-04. Header audio previously hid active status and Stop inside its settings disclosure. Compact header mode now keeps active status, pause/resume and Stop outside the disclosure; idle summary omits repeated volume/speed metadata but still identifies muted output. Settings remain available. Stop returns keyboard focus to the surviving summary. Existing embedded controls retain their detailed presentation.

Seven audio unit tests pass; lint/types/build pass. Two audio browser journeys verify persisted settings, preparation, pause/resume, Stop with settings closed and focus restoration. Three Park/layout checks pass. The 320px active-audio screenshot was inspected: controls wrap, Stop is visible, no horizontal overflow. Existing worker/bundle warnings remain.

No voice provider, audio owner or learning behavior changes. Physical Bluetooth output remains unverified. Compact header composition and reducing repeated embedded controls remain future work; active status intentionally takes space rather than hiding recovery.
