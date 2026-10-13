# Listening answer draft binding — R4

2026-10-13. Reproduced a cloze answer restored after the assessment returned changed wording/version. Multiple-choice listening already required reselection and is preserved. Review has no typed-answer field; its existing reveal-version guard is not replaced by this slice.

Listening now uses the shared exact-identity draft store, keeps earlier answers/unknown legacy text separately, and discloses failed persistence. The current question remains frozen during background refetch. Explicit practice refresh only carries text across unchanged displayed requirements; explicit submission recovery keeps the latest answer as requested. Stale refresh responses are rejected by question identity. Successful grading clears only the matched version and preserves edits made while grading. No audio engine, scoring, competency or scheduling change.

Verification:15 focused tests, including the reproduced changed-cloze case and existing edit-during-grading preservation; targeted lint and production build/type checks pass. Five sandbox browser journeys pass: two cloze version/reload/keyboard disclosure flows at390/1280, two listening practice/clip-position flows and one audio-owner handoff. Screenshots inspected at both widths, no horizontal overflow. Mocked media and API fixtures are explicitly used; no physical headphone/microphone or actual comprehension claim. Code review found no blocker/major. Recovery wording reuses the reviewed earlier-draft/storage-warning pattern.

Remaining: tab-local storage, no recovery after denied storage plus reload; no new expiry/purge. Review hint-version binding and other R4 surfaces remain separate. The assessment-policy decision remains pending; this fix does not authorize it.
