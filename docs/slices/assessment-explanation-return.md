# Keep checked feedback while revisiting an explanation

## Problem and reproduction — 2026-10-05

A real deterministic wrong-answer journey at390 and1280px reproduced feedback disappearing after Revisit the explanation → return to the question. AssessPanel unmounted during the teaching phase, discarding its frozen question and result. This made an ordinary help visit behave like starting again. Both pre-fix browser tests failed at the returned-feedback assertion.

## Implementation

Mount assessment only after the learner first enters it, then retain it hidden within that activity during explanation visits. Its query is disabled while hidden, help streaming is stopped, and reading-audio/recovery UI is unmounted. Existing received help and assessment state stay available on return. Session/block ownership continues to reset the component when moving to another activity. The explanation action says Return to your question once entered, and is available even if no explanation has been generated. Checked questions no longer ask the learner to choose an answer after answer controls have gone.

No grading, mastery, scheduling, publication or provider logic changed. This is in-page retention, not a new persistent assessment store. Refresh/navigation out of the activity still uses existing saved-feedback and submission recovery mechanisms.

## Verification

29 focused unit checks pass: existing assessment recovery suite, Session state/continuation tests, and hidden-help abort/late-token/retained-text check. Seven browser journeys pass, including real incorrect MCQ/cloze feedback at390/1280, optional omitted confidence, exactly one grading request across explanation return, completed-reading reload, interrupted-reply recovery, session clarity and existing visualizer recovery. After the final checked-question copy adjustment,29 unit and the two directly affected browser journeys pass again. Full lint/types pass; production build passed before that copy-only adjustment, with existing externalized worker_threads and bundle-size warnings.

Keyboard enters and returns to the same checked feedback. Narrow feedback screenshot inspected: original answer and correction readable, Continue/Revisit/optional next question reachable, no horizontal overflow. Independent code/pedagogy review found no actionable defect; hidden-help lifecycle coverage was added in response to its suggested test gap.

## Remaining

This does not close repeated-error adaptation, semantic model-feedback quality, pending-submit/navigation races, full refresh retention of the visible assessment result, physical audio or owner comprehension. Next inspect those broader feedback/recovery behaviors using existing durable outcomes; do not create duplicate learning evidence or regenerate grading just to restore a screen.
