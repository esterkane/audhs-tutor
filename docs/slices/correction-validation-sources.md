# Correction structure and source identities

Internal pre-editor checks only; no public draft endpoint, editor or publication is enabled. MCQ, cloze, explain-back/transfer and challenge candidates receive kind-specific shape problems. Code candidates explicitly require execution review; unknown kinds remain unsupported. Valid shape is not source support, teaching correctness or publication approval.

The validator never rewrites saved work. It rejects edits to non-editable metadata, including source links, clip settings, code links and challenge mode. Identity/ownership remain outside the candidate. MCQ options need a valid integer answer index and must remain distinct/nonempty under the actual deterministic grader normalization. Cloze answers must survive that normalization. Rubric criteria must be nonempty/distinct; challenge display criteria must match the rubric in order. Current graders and learning policy are unchanged.

New draft original snapshots include private source evidence: identified chunk/document version, text hash, timestamps and provenance fields. Reads compare content, eligibility revision and source identities independently. Missing sources/provenance, malformed references and excessive reference counts are incomplete; legacy citation-only labels are unresolved, never guessed. Old drafts without captured evidence say not_captured rather than being silently backfilled. Hashes/provenance remain server-private; this is not a public content API. Checks compare the referenced version, not whether a newer document version exists.

## Evidence

22 focused tests passed across validation, draft persistence and the correction inbox. Coverage includes invalid/ambiguous MCQ options, cloze normalization, rubric consistency, immutable metadata, changed text under an unchanged chunk ID/version, provenance changes, legacy drafts and incomplete source declarations. Strict mypy213 and Ruff pass. Bounded review caught MCQ normalized-option collisions; fixed and verified against the existing grader. No schema or frontend change, so unchanged migration/browser/build checks were reused.

## Remaining

Public draft commands and recovery lookup, typed editor with deliberate answer reselection, source passage preview, missing/updated-version resolution and semantic review remain. Changed listening wording requires a fresh clip-validation decision before publication; original validation flags must not be treated as fresh evidence. Code changes require their own sandbox execution review. Ownership/resolver/publication contracts remain disabled. Save alone never means validated, corrected or published.
