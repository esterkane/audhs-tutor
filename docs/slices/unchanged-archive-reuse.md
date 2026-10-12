# Unchanged archive reuse — 2026-10-12

Operational recovery tooling previously recompressed every snapshot with a current
gzip timestamp, changing a large binary part even when database bytes were identical.
The private archive tool now creates a fresh consistent SQLite backup and checks
integrity, then reuses an existing archive only after verifying manifest identity,
ordered part names/sizes/hashes and the decompressed database size/hash. Incomplete
or corrupt archives rebuild. Rebuilds use deterministic gzip timestamps. No prior
recovery point or learner data is deleted by the unchanged fast path.

Disposable SQLite regression covers unchanged byte-for-byte retention, changed
source data, damaged compressed data, valid metadata with a truncated compressed
segment and malformed metadata. All pass. Bounded review found an initial archive
completeness gap; decompressed validation and its regression resolve it. Final review
has no blockers/majors. Running the tool on the current database confirms verified
reuse with no database-part or manifest changes.

No application/runtime, learning logic or schema changed; existing application
checks are reused. The sanitized variant receives this generic operational record
only, never private archive tools or database snapshots. Both repositories remain
private. This reduces local compression/upload work, not model inference costs.
