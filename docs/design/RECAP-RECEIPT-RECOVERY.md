# Exact recap receipt recovery

Bounded R3/R4 reliability change. No grading or scheduling decision changes.

Problem: after the server commits a recap but its response is lost, the learner may edit the local draft. A retry currently returns the already-ended session without checking the recap, and the UI clears newer notes while showing success.

Contract:
- Existing immutable ENDED event is the receipt; no synthetic historical backfill or new evidence table.
- Owned read endpoint reports open, saved (validated matching session event) or unverified (ended without a trustworthy event). It exposes only the learner's own optional recap.
- New recap saves explicitly request exact receipt confirmation. First commit remains unchanged; retries whose canonical notes/ratings differ return a conflict. Plain End keeps existing first-completion behavior and sends no ratings.
- Browser reads status on opening recap and offers an explicit read-only Check saved recap after a failed save. Read failure preserves editable draft and retry; no automatic completion POST.
- Saved receipt and current browser draft are displayed separately. Different/unknown saved state never clears or overwrites local work. Ended sessions cannot accept a replacement recap in this slice. Copying retained local notes and leaving remain possible.
- Normal confirmed saves retain the existing summary. Reload may show the saved receipt instead; the same session ID/draft is retained until an explicit exit.

Verify real committed/lost response plus edited retry, exact replay, empty canonical values, unknown/legacy receipt, foreign learner denial, status-read failure, reload, keyboard and narrow layout. Existing API outer block/recall/checkpoint transaction reconciliation remains a separate task.
