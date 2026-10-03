# Material coverage reconciliation

Acquisition, local-file presence, ingestion, search indexing and usable notebook execution are different states. A missing exact file-path match must not be presented as missing learning content without checking relocated duplicates and recorded recovery evidence.

The private acquisition audit now refreshes the existing local link ledger and examines notebook gaps against a read-only database. It distinguishes byte-identical copies of ingested files, invalid or empty notebook files, and partial text recovery linked to an existing document version. Byte equality establishes identity between the current local files, not equality to the stored ingested version, execution correctness or provenance completeness. Historical parser errors remain intact.

Failed downloads are triaged rather than automatically retried: unsupported URL schemes, oversized repository archives, redirects, gone resources, access restrictions and server errors need different follow-up. This does not authorize bypassing access controls, silently rewriting source URLs, or downloading an entire repository beyond its configured bound.

Detailed URLs, acquisition scripts, reports and course materials remain only in the private archive. The sanitized application gains no acquisition code, learner data or platform-specific configuration. The account-backed course inventory still requires a signed-in browser; existing local records cannot establish exhaustive platform coverage.

Validation: the bounded audit completed against local files and a read-only database. A synthetic temporary-file/database regression covers hash matches and nonmatches, malformed JSON, zero-byte files, valid empty cell arrays, and present/missing recovery versions. Independent implementation and root review clarified that file identity is not ingested-version equality. Detailed counts and paths are recorded only in the private handoff and reports. No notebook code, hosted model, assessment submission or learner progress mutation is involved.
