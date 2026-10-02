# Browser voice result recovery

A learner returning to an interrupted identified voice request can explicitly check for saved
text without sending the question, opening a microphone or playing audio. The tab stores its
UUID before typed/capture admission, scoped by session/skill/language/conversation. Normal
terminal delivery clears the matching pending request; uncertain failures keep it. Existing
unidentified servers remain compatible but cannot offer durable request recovery.

Pending requests block new questions until checked/dismissed. Check closes the connection and
uses the owned read-only endpoint. Missing, unresolved, partial and completed results have
separate explanations. Terminal text enters the existing scoped text cache; dismissal and reload
preserve it and the next typed draft. Dismissal does not cancel server work or delete saved answers.
It authorizes a new request, never a retry of raw audio. No mastery/checkpoint/event writes, mode
changes, paid calls or automatic playback. Controls are keyboard accessible on narrow/desktop.

Storage denial prevents sending until an explicit page-only choice. Clearing failures keep the
pending identity; corrupt storage can be explicitly cleared. Lookups have a 15-second deadline,
abort on disposal, and reject stale results even when transport ignores cancellation. Request IDs
contain no audio. Stored answer-save receipts are not included in the browser text cache.

## Review fixes and verification

Code review found an unbounded GET; added deadline, abort and stale-result regression tests.
Pedagogy review found disappearing recovered text and a stale malformed-storage guard; terminal
text now enters the existing cache and clearing resets the guard. Tests cover admission-before-send,
reload, all four result states, storage denial, failed clear, stale terminal/lookup and stalled GET.
Frontend 273 tests passed (38 voice-focused), lint/types and production build passed, and two
isolated keyboard desktop/narrow browser journeys passed with zero voice connections. Required
code and pedagogy re-reviews have no remaining blockers/majors. Existing build chunk warning remains.

Provider-resistant backend teardown and the personal-recordings benchmark remain open. This is
not an exactly-once provider guarantee; voice transcription precedes the durable response claim.
