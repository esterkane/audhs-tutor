# Session explanation entry

The session learning goal was incorrectly labeled “Listen to explanation”, although it contained only the objective. The actual explanation required another action below an empty question field.

The goal is now labeled Learning goal / Listen to learning goal. The teaching panel leads with Your explanation, an explicit empty-state explanation and Start explanation before the optional question field. Generated teaching text retains its own Listen control. No automatic generation or audio was added; practice still requires completed teaching in this flow. Existing interrupted-response recovery remains unchanged.

Validation (2026-10-03): 16 Session/read-aloud tests, targeted ESLint and production build passed. Three isolated browser journeys passed (explanation reader, session clarity, voice-reading coordination); the session-clarity fixture needed its old heading updated before passing. Existing build bundle-size and worker_threads warnings remain. Independent review found no blockers or majors. A local synthetic speech request returned non-silent PCM, which does not establish physical headphone audibility. No learner session was mutated by browser tests.
