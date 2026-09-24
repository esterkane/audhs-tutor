# ADR-0016: Learner-controlled sessions and optional confidence

Status: Accepted (owner request, 2026-09-24)

The owner reported repeated confidence questions, unexplained assessment prompts, unclear exits and unrelated seed questions after selecting a knowledge area.

- Explicit area/course choices restrict lessons and due reviews to that scope and genuine prerequisites. No available lesson is an actionable empty state, never a whole-map fallback. Starting snapshots the selection; changing the default does not silently rewrite an existing session.
- Confidence is optional, collapsed and nullable. Omission is not neutral confidence. Stops require neither an assessment nor recap ratings. This supersedes prior mandatory-confidence UX guidance.
- Questions offer context, a hint and an explanation in place. Delivered assistance is retained with the answer draft. Assisted review is logged and capped at Hard so it is not recorded as unaided Easy recall.
- Clear/later labels are reversible explicit bookmarks, stored under the closed `learning.material_marks` preference. They do not change competency or FSRS; the learner can revisit a saved lesson explicitly.
- Read-aloud uses the existing local TTS route, without microphone access, automatic playback or a hosted fallback. It logs model calls and stops when its view is closed. The current Kokoro voice option is labelled English; multilingual speech quality is not claimed.

No new dependency or database migration. Existing active lessons and learner history remain intact; draft activation remains explicit.
