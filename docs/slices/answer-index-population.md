# Local answer embedding population

`uv run --project backend python scripts/index_answers.py --limit 100` populates missing eligible workspace answer vectors. Repeat to continue bounded batches. `--rebuild` recomputes the selected first batch; it is not a whole-library background job.
Only an already-installed loopback Ollama embedding route is allowed. Cache identity hashes format version, registry ID, model tag and installed artifact digest. No download, hosted call, generation or evidence write. Each embedding attempt logs model identity and duration.
Hidden/incorrect/outdated and memory-derived replies are excluded before limiting. Answer fingerprint is rechecked on write. Existing cache hits avoid embedding. Batches of 16 release the read transaction before inference; completed batches persist if a later one fails. Invalid/nonfinite/mixed-dimension responses fail without caching that batch.
The script is explicit local maintenance, not yet a tutor-time semantic path. Corrupt cached entries need explicit rebuild. No task-level semantic ranking or background automatic population has been enabled.

Live smoke run: installed route/digest resolved; selected/indexed/skipped all zero (no eligible saved workspace answers in the current database). No private materials or invented answers were added. Synthetic tests populate multiple entries, skip existing/flagged/history-derived entries, verify no inference transaction and log failures.
Verification: 462 backend tests before review fix; three focused indexing tests after the fix, lint/types passed. Review found and fixed an open read transaction after a skipped final batch write; 17-answer regression verifies the next embedding starts outside a transaction. Re-review clear.
