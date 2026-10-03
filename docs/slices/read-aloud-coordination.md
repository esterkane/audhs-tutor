# One requested reading at a time (UX26-06)

Starting a question, explanation or saved-answer reading stops the previous requested reading,
including one still preparing or paused. Tell the learner why it stopped; never start automatically.
Coordinate only ReadAloud owners in this browser tab. Release by identity so stale completion or
unmount cannot stop a newer reading. No stored state, model routing, API or learning events change.
Verify two mounted readings, late synthesis and release identity; retain keyboard controls.
Voice conversation, media players and global transport controls remain separate follow-up work.

## Verification
Reproduced overlapping synthesis before fix: earlier request was not aborted (8 pass, 1 fail).
Full frontend322 / 83 files; focused11; two existing isolated audio browser journeys passed.
New component regression covers two concurrent readers, abort and late response; unit tests cover
stale release and finished ownership. Browser journeys cover transport/settings, not two-reader overlap.
Lint/build passed with existing chunk/worker warnings. Code/pedagogy review: no blockers or majors.
No physical audibility or owner-comprehension claim; broader audio coordination remains open.
